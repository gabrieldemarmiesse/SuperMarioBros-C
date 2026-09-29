"""Isolated FCEUX process and bounded, serialized file-IPC requests."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid

from PIL import Image

from .movie import inspect_movie

BUTTONS = frozenset(('A', 'B', 'select', 'start', 'up', 'down', 'left', 'right'))
BRIDGE = Path(__file__).parent / 'systems' / 'nes' / 'bridge.lua'


def integer(value: int, low: int, high: int, name: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer from {low} to {high}')
    return value


def button_string(buttons: list[str]) -> str:
    if not isinstance(buttons, list) or any(b not in BUTTONS for b in buttons):
        raise ValueError(f'Buttons must be a list drawn from {sorted(BUTTONS)}')
    if {'left', 'right'} <= set(buttons) or {'up', 'down'} <= set(buttons):
        raise ValueError('Opposite directions are not supported')
    return ','.join(sorted(set(buttons)))


def gd_to_png(data: bytes) -> bytes:
    if len(data) < 11 or data[:2] != b'\xff\xfe' or data[6] != 1:
        raise ValueError('Invalid FCEUX truecolor screenshot')
    width, height = int.from_bytes(data[2:4], 'big'), int.from_bytes(data[4:6], 'big')
    if (width, height) != (256, 240) or len(data) != 11 + width * height * 4:
        raise ValueError('Unexpected screenshot dimensions or length')
    image = Image.frombytes('RGB', (width, height), data[11:], 'raw', 'XRGB')
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


class Session:
    def __init__(self, rom_path: str, output_dir: str | None = None):
        rom = Path(rom_path).expanduser().resolve(strict=True)
        if not rom.is_file() or rom.stat().st_size > 64 * 1024 * 1024:
            raise ValueError('Expected an NES cartridge file smaller than 64 MiB')
        raw = rom.read_bytes()
        if len(raw) < 16 or raw[:4] != b'NES\x1a':
            raise ValueError('Only iNES/NES 2.0 cartridge images are supported')
        # Require complete standard iNES payload. NES 2.0 extended sizes are
        # delegated to FCEUX; callers still receive the exact input hash.
        if raw[7] & 0x0c != 0x08:
            expected = 16 + (512 if raw[6] & 4 else 0) + raw[4]*16384 + raw[5]*8192
            if raw[4] == 0 or len(raw) < expected:
                raise ValueError('Truncated or empty iNES PRG image')
        exe = os.environ.get('FCEUX_PATH') or shutil.which('fceux')
        if not exe:
            raise RuntimeError('FCEUX not found. Install it or set FCEUX_PATH.')
        self.id = uuid.uuid4().hex
        base = Path(output_dir).expanduser() if output_dir else Path.home()/'.local/share/emulator-use/sessions'
        self.root = base.resolve()/self.id
        self.root.mkdir(parents=True, mode=0o700)
        self.lock = threading.RLock()
        self.process = None
        self.log = None
        self.closed = False
        self.seq = 0
        self.checkpoints: set[str] = set()
        self.initial_ram_sha256 = None
        self.movie = None
        target = self.root/'game.nes'
        target.write_bytes(raw)
        config = self.root/'fceux-config'
        config.mkdir()
        self.metadata = {'session_id': self.id, 'rom_path': str(rom),
                         'rom_sha256': hashlib.sha256(raw).hexdigest(),
                         'system': 'nes', 'backend': 'fceux', 'session_dir': str(self.root),
                         'frame_convention': 'completed frames since bridge ready; restored with checkpoints',
                         'capabilities': ['step', 'screenshot', 'checkpoint', 'read_internal_ram', 'registers', 'watch_writes', 'fm2_replay', 'speed_control'],
                         'limitations': ['GUI display required', 'CPU-only watch PC; physical mapper bank unresolved',
                                         'checkpoints load only within their originating session',
                                         'no arbitrary Lua, ROM writes, or MMIO reads']}
        try:
            env = dict(os.environ, EMULATOR_USE_SESSION=str(self.root), FCEUX_CONFIG_DIR=str(config))
            version = subprocess.run([exe, '--help'], env=env, capture_output=True, text=True, timeout=10)
            self.metadata['emulator_version_output'] = version.stdout[:1000]
            self.log = (self.root/'emulator.log').open('wb')
            self.process = subprocess.Popen(
                [exe, '--no-config','1','--sound','0','--frameskip','0',
                 '--loadstate','99','--savestate','99','--periodicsaves','0',
                 '--loadlua',str(BRIDGE),str(target)],
                cwd=self.root, env=env, stdout=self.log, stderr=self.log, start_new_session=True)
            ready = self._wait_json(self.root/'ready.json', 20)
            if ready.get('protocol') != 1 or not ready.get('paused'):
                raise RuntimeError('Emulator bridge did not enter a paused state')
            if Path(ready['rom']).name not in (target.name, target.stem):
                raise RuntimeError('Emulator loaded an unexpected ROM')
            self.metadata['initial_status'] = ready
            self._write_metadata()
            self.initial_ram_sha256 = self.ram(0, 2048)['sha256']
            self.metadata['initial_ram_sha256'] = self.initial_ram_sha256
            self._write_metadata()
        except BaseException:
            self.close()
            raise

    def _write_metadata(self):
        (self.root/'session.json').write_text(json.dumps(self.metadata, indent=2))

    def _wait_json(self, path: Path, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return json.loads(path.read_text())
            if self.process is None or self.process.poll() is not None:
                raise RuntimeError(f'Emulator exited; inspect {self.root / "emulator.log"}')
            time.sleep(0.02)
        raise TimeoutError(f'Emulator command timed out; inspect {self.root / "emulator.log"}')

    def command(self, operation: str, *args, timeout: float = 20) -> dict:
        with self.lock:
            if self.closed:
                raise RuntimeError('Session is closed; open a new session')
            self.seq += 1
            request_id = f'{self.seq:08d}'
            values = [request_id, operation, *(str(a) for a in args)]
            if any('\n' in v or '\r' in v for v in values):
                raise ValueError('Invalid command field')
            response = self.root/'response.json'
            response.unlink(missing_ok=True)
            request = self.root/'request.tmp'
            request.write_text('\n'.join(values)+'\n')
            request.replace(self.root/'request.txt')
            log = {'id': request_id, 'operation': operation, 'args': args}
            try:
                result = self._wait_json(response, timeout)
                if result.get('id') != request_id:
                    raise RuntimeError('Bridge response ID mismatch')
                if 'error' in result:
                    raise RuntimeError(result['error'])
                log['result'] = result
                return result
            except BaseException as error:
                log['error'] = str(error)
                # Abort the owned process on uncertainty: never allow an input
                # request to keep running after the caller has timed out.
                self.close()
                raise
            finally:
                with (self.root/'events.jsonl').open('a') as f:
                    f.write(json.dumps(log)+'\n')

    def status(self):
        return self.command('status')

    def set_speed(self, mode: str):
        if mode not in ('normal', 'unthrottled'):
            raise ValueError('Speed must be normal or unthrottled')
        return self.command('speed', mode)

    def load_movie(self, movie_path: str):
        raw, metadata = inspect_movie(movie_path)
        with self.lock:
            current = self.status()
            if self.movie is not None or self.checkpoints or current['frame'] != 0:
                raise ValueError('Load a movie into a fresh session before stepping or saving checkpoints')
            if metadata['rom_md5'] != current['rom_md5'].lower():
                raise ValueError('FM2 ROM checksum does not match the loaded cartridge')
            target = self.root / 'replay.fm2'
            target.write_bytes(raw)
            result = self.command('movie')
            if result['movie']['length'] != metadata['frames']:
                self.close()
                raise RuntimeError('FCEUX movie length differs from inspected FM2 length')
            self.movie = metadata
            self.metadata['movie'] = metadata | {'copy': str(target), 'readonly': True}
            self._write_metadata()
            return result | {'movie_identity': self.metadata['movie']}

    def _movie_buttons(self, buttons):
        if self.movie is not None and buttons:
            raise ValueError('Movie replay owns controller inputs; omit buttons')

    def step(self, frames: int, buttons: list[str]):
        integer(frames, 1, 600, 'frames')
        self._movie_buttons(buttons)
        return self.command('step', frames, button_string(buttons))

    def ram(self, address: int, length: int):
        integer(address, 0, 2047, 'address')
        integer(length, 1, 2048-address, 'length')
        result = self.command('ram', address, length)
        result['sha256'] = hashlib.sha256(bytes(result['bytes'])).hexdigest()
        return result

    def screenshot(self):
        with self.lock:
            result = self.command('screenshot')
            source = self.root/result['file']
            data = gd_to_png(source.read_bytes())
            png = source.with_suffix('.png')
            png.write_bytes(data)
            return result | {'file': str(png), 'png': data}

    def checkpoint(self, name: str, load: bool = False):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', name):
            raise ValueError('Checkpoint name must be 1-48 letters, digits, underscores, or hyphens')
        with self.lock:
            if load and name not in self.checkpoints:
                raise ValueError('Unknown checkpoint in this session')
            if not load and name in self.checkpoints:
                raise ValueError('Checkpoint already exists; choose a new name')
            result = self.command('load' if load else 'save', name)
            if not load:
                self.checkpoints.add(name)
            return result

    def watch(self, address: int, frames: int, buttons: list[str], max_events: int = 128):
        integer(address, 0, 2047, 'address')
        integer(frames, 1, 120, 'frames')
        integer(max_events, 1, 512, 'max_events')
        self._movie_buttons(buttons)
        return self.command('watch', frames, button_string(buttons), address, max_events)

    def close(self):
        with self.lock:
            if self.closed:
                return {'closed': True, 'session_dir': str(self.root)}
            self.closed = True
            if self.process and self.process.poll() is None:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                    self.process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=3)
                except ProcessLookupError:
                    pass
            if self.log:
                self.log.close()
            return {'closed': True, 'session_dir': str(self.root)}

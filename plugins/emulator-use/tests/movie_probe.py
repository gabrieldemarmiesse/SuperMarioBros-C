"""Opt-in native FM2 replay test against a local Super Mario Bros. ROM."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import uuid

from emulator_use.backend import Session


def make_movie(path, rom_md5):
    header = [
        'version 3', 'emuVersion 20606', 'rerecordCount 0', 'palFlag 0',
        'romFilename game',
        'romChecksum base64:' + base64.b64encode(bytes.fromhex(rom_md5)).decode(),
        'guid ' + str(uuid.uuid4()), 'fourscore 0', 'port0 1', 'port1 0', 'port2 0',
    ]
    rows = ['|0|........|||'] * 120 + ['|0|....T...|||']
    rows += ['|0|........|||'] * 210 + ['|0|R.......|||'] * 60
    rows += ['|0|........|||'] * 30
    path.write_text('\n'.join(header + rows) + '\n')
    return len(rows)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        movie = Path(tmp)/'recorded inputs.fm2'
        s = Session(sys.argv[1])
        try:
            frames = make_movie(movie,s.status()['rom_md5'])
            original = hashlib.sha256(movie.read_bytes()).hexdigest()
            opened = s.load_movie(str(movie))
            assert opened['movie']['length'] == frames
            assert s.step(120,[])['frame'] == 120
            s.checkpoint('title')
            assert s.step(211,[])['frame'] == 331
            s.checkpoint('game')
            start = s.ram(0,2048)['sha256']
            assert s.step(30,[])['frame'] == 361
            expected_ram = s.ram(0,2048)['sha256']
            expected_image = s.screenshot()
            print('REPLAY_IMAGE',expected_image['file'],flush=True)
            s.checkpoint('game',load=True)
            assert s.ram(0,2048)['sha256'] == start
            speed = s.set_speed('unthrottled')
            assert speed['frame'] == 331 and speed['paused']
            assert speed['speed'] == 'unthrottled'
            s.step(30,[])
            assert s.ram(0,2048)['sha256'] == expected_ram
            assert s.screenshot()['png'] == expected_image['png']
            end = s.step(600,[])
            assert end['frame'] == frames and end['frames_advanced'] == frames-361
            assert s.step(5,[])['frames_advanced'] == 0
            for invoke in [lambda: s.step(1,['right']), lambda: s.watch(0,1,['A'])]:
                try: invoke()
                except ValueError: pass
                else: raise AssertionError('Manual input overrode movie playback')
            s.checkpoint('title',load=True)
            assert s.status()['speed'] == 'unthrottled'
            speed = s.set_speed('normal')
            assert speed['frame'] == 120 and speed['paused']
            assert speed['speed'] == 'normal'
            assert s.step(211,[])['frame'] == 331
            assert s.ram(0,2048)['sha256'] == start
            assert hashlib.sha256(movie.read_bytes()).hexdigest() == original
            assert (s.root/'replay.fm2').read_bytes() == movie.read_bytes()
            summary={'frames':frames,'final_ram_sha256':expected_ram,'movie_sha256':original}
            print('PASS: native movie input, checkpoint rewind, RAM/image replay, EOF clipping, source immutability',json.dumps(summary),flush=True)
        finally: s.close()
        # A separate process must reproduce the same scene without its old checkpoints.
        replay = Session(sys.argv[1])
        try:
            replay.load_movie(str(movie)); replay.set_speed('unthrottled'); replay.step(361,[])
            assert replay.ram(0,2048)['sha256'] == expected_ram
            assert replay.screenshot()['png'] == expected_image['png']
            print('PASS: unthrottled FM2 replay matches normal-speed RAM and framebuffer in a fresh session',flush=True)
        finally: replay.close()


if __name__ == '__main__':
    main()

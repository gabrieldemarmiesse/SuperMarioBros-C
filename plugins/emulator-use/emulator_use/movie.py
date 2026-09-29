"""Inspect FM2 identity before passing playback to FCEUX (not an input emulator)."""
import base64
import binascii
import hashlib
from pathlib import Path


def inspect_movie(path: str) -> tuple[bytes, dict]:
    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file() or source.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Expected a text FM2 file smaller than 32 MiB')
    raw = source.read_bytes()
    header = {}
    records = []
    in_records = False
    for line in raw.splitlines():
        if line.startswith(b'|'):
            in_records = True
            records.append(line)
        elif not in_records and line.strip():
            try:
                key, value = line.decode('utf-8').split(' ', 1)
            except (UnicodeDecodeError, ValueError) as error:
                raise ValueError('Invalid text FM2 header') from error
            if not header and key != 'version':
                raise ValueError('FM2 must start with version 3')
            if key in header and key not in ('comment', 'subtitle'):
                raise ValueError(f'Duplicate FM2 header: {key}')
            header[key] = value
        elif in_records and line.strip():
            raise ValueError('Unexpected non-input data after FM2 input records')
    if header.get('version') != '3':
        raise ValueError('Only FM2 version 3 is supported')
    if header.get('binary', '0') != '0':
        raise ValueError('Only text FM2 movies are supported')
    if any(header.get(k, '0') != '0' for k in ('FDS', 'fourscore', 'port2')):
        raise ValueError('Only NES movies with standard controller ports are supported')
    for key in ('port0', 'port1'):
        if header.get(key) not in ('0', '1'):
            raise ValueError('FM2 controller ports must be none or gamepad')
    for key in ('palFlag', 'NewPPU'):
        if header.get(key, '0') not in ('0', '1'):
            raise ValueError(f'Invalid FM2 {key}')
    if 'savestate' in header:
        raise ValueError('Use a power-on FM2 movie; embedded savestate starts are not supported')
    if not records:
        raise ValueError('FM2 has no input records')
    try:
        declared = int(header.get('length', '-1'))
        if declared >= 0 and declared != len(records):
            raise ValueError('FM2 length does not match its input records')
        checksum = header['romChecksum']
        if checksum.startswith('base64:'):
            digest = base64.b64decode(checksum[7:], validate=True)
        elif checksum.startswith('0x'):
            digest = bytes.fromhex(checksum[2:])
        else:
            raise ValueError('FM2 ROM checksum must use base64: or 0x encoding')
        if len(digest) != 16:
            raise ValueError('FM2 ROM checksum must be an MD5 digest')
        for row in records:
            parts = row.split(b'|')
            if len(parts) != 6 or parts[0] or parts[-1] or parts[4]:
                raise ValueError('Invalid FM2 input record')
            if not parts[1].isdigit() or int(parts[1]) & ~3:
                raise ValueError('Only reset/power commands are supported in this NES movie')
            for key, port in zip(('port0','port1'),parts[2:4]):
                expected = 8 if header[key] == '1' else 0
                if len(port) != expected or any(c < 32 or c > 126 for c in port):
                    raise ValueError('Invalid FM2 gamepad record')
    except (KeyError, binascii.Error) as error:
        raise ValueError('Missing or invalid FM2 ROM checksum') from error
    return raw, {'source': str(source), 'sha256': hashlib.sha256(raw).hexdigest(),
                 'rom_md5': digest.hex(), 'frames': len(records),
                 'rom_filename': header.get('romFilename', ''),
                 'recorded_emu_version': header.get('emuVersion', ''),
                 'pal': header.get('palFlag', '0') == '1',
                 'new_ppu': header.get('NewPPU', '0') == '1'}

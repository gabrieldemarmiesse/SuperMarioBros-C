import io
import struct
import subprocess
import threading
from pathlib import Path
from unittest.mock import Mock

from PIL import Image
import pytest

from emulator_use.backend import Session, button_string, integer, gd_to_png


def test_buttons_are_explicit_and_validated():
    assert button_string([]) == ''
    assert button_string(['right', 'A', 'A']) == 'A,right'
    for invalid in [['left','right'], ['up','down'], ['reset'], ['A\nstep'], 'A']:
        with pytest.raises(ValueError):
            button_string(invalid)


def test_frame_limits_reject_bool_fraction_and_overflow():
    for value in [True, 0, 601, 1.5, '12']:
        with pytest.raises(ValueError):
            integer(value, 1, 600, 'frames')


def test_invalid_speed_never_reaches_bridge(tmp_path):
    s = bare_session(tmp_path)
    s.command = Mock()
    for mode in ['turbo', 'maximum', 'normal\nstep', '', 2, None]:
        with pytest.raises(ValueError):
            s.set_speed(mode)
    s.command.assert_not_called()


def test_screenshot_channel_order_and_shape():
    raw=b'\xff\xfe'+struct.pack('>HH',256,240)+b'\x01\xff\xff\xff\xff'+bytes([0,12,34,56])*(256*240)
    image=Image.open(io.BytesIO(gd_to_png(raw)))
    assert image.size == (256,240)
    assert image.getpixel((0,0)) == (12,34,56)
    for invalid in [b'',raw[:-1],raw.replace(b'\xff\xfe',b'\x00\x00',1)]:
        with pytest.raises(ValueError): gd_to_png(invalid)


def bare_session(tmp_path):
    s=Session.__new__(Session)
    s.lock=threading.RLock()
    s.root=tmp_path
    s.seq=0
    s.closed=False
    s.checkpoints=set()
    s.movie=None
    s.close=Mock()
    return s


def test_timeout_closes_session_and_records_request(tmp_path):
    s=bare_session(tmp_path)
    s._wait_json=Mock(side_effect=TimeoutError('probe timeout'))
    with pytest.raises(TimeoutError): s.command('step',600,'right')
    s.close.assert_called_once()
    assert 'probe timeout' in (tmp_path/'events.jsonl').read_text()


def test_response_mismatch_closes_session(tmp_path):
    s=bare_session(tmp_path)
    s._wait_json=Mock(return_value={'id':'old'})
    with pytest.raises(RuntimeError,match='ID mismatch'): s.command('status')
    s.close.assert_called_once()


def test_ram_and_checkpoint_boundaries_never_reach_bridge(tmp_path):
    s=bare_session(tmp_path)
    s.command=Mock()
    for address,length in [(2048,1),(-1,1),(2047,2),(0,0)]:
        with pytest.raises(ValueError): s.ram(address,length)
    for name in ['../save','x\nstep','', 'a'*49]:
        with pytest.raises(ValueError): s.checkpoint(name)
    with pytest.raises(ValueError): s.checkpoint('missing',load=True)
    s.checkpoints.add('existing')
    with pytest.raises(ValueError): s.checkpoint('existing')
    s.command.assert_not_called()


def test_invalid_rom_rejected_before_launch(tmp_path):
    bad=tmp_path/'game.nes'
    for data in [b'no',b'NES\x1a'+bytes([2,1])+bytes(10)]:
        bad.write_bytes(data)
        with pytest.raises(ValueError): Session(str(bad))


def test_close_stops_an_owned_process_that_ignores_sigterm(tmp_path):
    import sys
    process = subprocess.Popen(
        [sys.executable, '-c',
         'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
         'print("ready",flush=True); time.sleep(30)'],
        stdout=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        assert process.stdout.readline().strip() == 'ready'
        s = Session.__new__(Session)
        s.root = tmp_path
        s.lock = threading.RLock()
        s.closed = False
        s.process = process
        s.log = None
        assert s.close()['closed']
        assert process.poll() is not None
        assert s.close()['closed']
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()

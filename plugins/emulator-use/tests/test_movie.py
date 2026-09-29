import base64
import hashlib
from unittest.mock import Mock

import pytest

from emulator_use.movie import inspect_movie
from tests.movie_probe import make_movie
from tests.test_backend import bare_session


def test_inspect_movie_records_identity_without_changing_source(tmp_path):
    p=tmp_path/'inputs.fm2'
    digest='12'*16
    frames=make_movie(p,digest)
    before=p.read_bytes()
    raw,meta=inspect_movie(str(p))
    assert raw==before==p.read_bytes()
    assert meta['frames']==frames==421
    assert meta['rom_md5']==digest
    assert meta['sha256']==hashlib.sha256(before).hexdigest()
    assert not meta['pal']


@pytest.mark.parametrize('old,new',[
    ('version 3','version 2'),
    ('port0 1','port0 2'),
    ('fourscore 0','fourscore 1'),
    ('port2 0','port2 1'),
    ('palFlag 0','palFlag 2'),
    ('|0|........|||','|16|........|||'),
    ('|0|........|||','|0|short|||'),
    ('|0|........|||','|0|........|A||'),
])
def test_reject_unsupported_movie_records(tmp_path,old,new):
    p=tmp_path/'inputs.fm2'; make_movie(p,'12'*16)
    p.write_text(p.read_text().replace(old,new))
    with pytest.raises(ValueError): inspect_movie(str(p))


@pytest.mark.parametrize('header',[
    'binary 1', 'savestate 0x00', 'length 1', 'version 3',
    'romChecksum base64:invalid', 'romChecksum 0x12',
])
def test_reject_ambiguous_or_unsupported_headers(tmp_path,header):
    p=tmp_path/'inputs.fm2'; make_movie(p,'12'*16)
    p.write_text(p.read_text().replace('fourscore 0',header+'\nfourscore 0'))
    with pytest.raises(ValueError): inspect_movie(str(p))


def test_checksum_mismatch_never_reaches_movie_loader(tmp_path):
    p=tmp_path/'inputs.fm2'; make_movie(p,'12'*16)
    s=bare_session(tmp_path)
    s.status=Mock(return_value={'frame':0,'rom_md5':'34'*16})
    s.command=Mock()
    with pytest.raises(ValueError,match='checksum'): s.load_movie(str(p))
    s.command.assert_not_called()
    assert not (tmp_path/'replay.fm2').exists()


def test_movie_input_ownership_and_fresh_session_guard(tmp_path):
    p=tmp_path/'inputs.fm2'; make_movie(p,'12'*16)
    s=bare_session(tmp_path)
    s.status=Mock(return_value={'frame':1,'rom_md5':'12'*16})
    s.command=Mock()
    with pytest.raises(ValueError,match='fresh session'): s.load_movie(str(p))
    s.movie={'frames':421}
    with pytest.raises(ValueError,match='owns controller'): s.step(1,['A'])
    with pytest.raises(ValueError,match='owns controller'): s.watch(0,1,['A'])
    s.command.assert_not_called()


def test_crlf_hex_digest_and_reset_commands(tmp_path):
    p=tmp_path/'inputs.fm2'; make_movie(p,'12'*16)
    text=p.read_text().replace('base64:'+base64.b64encode(bytes.fromhex('12'*16)).decode(),'0x'+'12'*16)
    text=text.replace('|0|........|||','|2|........|||',1)
    p.write_bytes(text.replace('\n','\r\n').encode())
    assert inspect_movie(str(p))[1]['rom_md5']=='12'*16

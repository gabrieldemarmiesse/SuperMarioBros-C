"""Opt-in real FCEUX exercise. Run from plugin root with a local ROM argument."""
import json
from pathlib import Path
import sys
import time
from emulator_use.backend import Session

session = Session(sys.argv[1])
try:
    print('SESSION',session.root,flush=True)
    first=session.status()
    time.sleep(0.2)
    assert session.status()['frame']==first['frame']==0
    assert session.status()['emulator_frame']==first['emulator_frame']
    assert session.step(120,[])['frame']==120
    shot=session.screenshot(); print('TITLE',shot['file'],flush=True)
    session.checkpoint('title')
    before=session.ram(0,2048)['sha256']
    session.step(1,['start']); session.step(210,[])
    shot=session.screenshot(); print('GAME',shot['file'],flush=True)
    session.checkpoint('game')
    start=session.ram(0,2048)
    session.step(30,[])
    control=session.ram(0,2048)
    control_screen=session.screenshot()['png']
    session.checkpoint('game',load=True)
    assert session.ram(0,2048)['sha256']==start['sha256']
    session.step(30,['right'])
    action=session.ram(0,2048)
    first_action=session.screenshot()
    assert first_action['png'] != control_screen,'Input produced no visual difference'
    session.checkpoint('game',load=True)
    session.step(30,['right'])
    repeat=session.ram(0,2048)
    assert repeat['sha256']==action['sha256'],'RAM replay mismatch'
    assert session.screenshot()['png']==first_action['png'],'Frame replay mismatch'
    changes=[i for i,(a,b) in enumerate(zip(control['bytes'],action['bytes'])) if a!=b]
    assert changes,'Input produced no RAM differences'
    session.checkpoint('game',load=True)
    watched=session.watch(changes[0],30,['right'],8)
    assert watched['paused']
    assert watched['event_count'] > 0
    assert len(watched['events']) <= 8
    assert watched['truncated'] == (watched['event_count'] > 8)
    print('WATCH',json.dumps(watched),flush=True)
    session.checkpoint('title',load=True)
    assert session.ram(0,2048)['sha256']==before
    print('PASS: idle pause, exact stepping, PNG, checkpoint restore, input effect, deterministic replay',flush=True)
finally:
    session.close()

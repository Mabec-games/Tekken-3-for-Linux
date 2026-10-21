#!/usr/bin/env python3
"""Isolated selector/attack smoke test; requires private assets and fixtures."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import time
from launch_jun_preview import ROOT,launch,debug_client

def check(jun):
    work=ROOT/'workspace/jun-import'
    info=launch(ROOT/'build-debug-server-lite',work,headless=True,selector=True,muted=True)
    q=lambda r:debug_client.query('127.0.0.1',info['port'],r)
    read=lambda a,n:bytes.fromhex(q(dict(cmd='read_ram',addr=f'{a:08x}',len=n))['hex'])
    def write(a,v,n=4):
        for i in range(n):q(dict(cmd='write_ram',addr=f'{a+i:08x}',val=f'{(v>>(8*i))&255:02x}'))
    def press(button):
        assert q(dict(cmd='set_input',buttons=button))['ok']
        time.sleep(.16)
        q(dict(cmd='set_input',buttons=0xffff))
        time.sleep(.16)
    try:
        for _ in range(12):
            if read(0x80098106,1)==b'\x09':break
            press(0xffdf)
        else:raise AssertionError('Could not highlight Jin')
        press(0xfeff)  # Jun
        if not jun:press(0xfeff)  # Jin remains available
        press(0xbfff if jun else 0x7fff)
        control=int(info['control'],16)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            base=struct.unpack('<I',read(0x8009bd28,4))[0]
            mode=struct.unpack('<I',read(0x800ae204,4))[0]
            if mode==8 and 0x80100000<=base<=0x801f8000:
                row=struct.unpack('<I',read(base+24,4))[0]
                if (jun and row==0x9f0006e8) or (not jun and row==base+0x620):break
            time.sleep(.2)
        else:raise AssertionError('Selected model did not load')
        assert read(control,1)==bytes([int(jun)])
        assert read(control+12,1)==bytes([2 if jun else 0])
        log=Path(info['log'])
        if not jun:
            assert 'Jun combat: loaded' not in log.read_text()
            print('PASS Jun -> Jin toggle: native Jin model and moves retained',flush=True)
            return
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            text=log.read_text()
            if 'donor pose reached native skeleton bridge' in text:break
            time.sleep(.2)
        else:raise AssertionError('Arcade pose bridge did not run')
        guest=int(re.search(r'(?:experimental|source) records and \d+ input sequences at ([0-9A-F]+)',text)[1],16)
        p=(work/'jun/Jun-TTT1-combat.jmv').read_bytes();h=struct.unpack_from('<8I',p)
        record_base=int(re.findall(r'installed P1 alias table,.*records=([0-9A-F]+)',text)[-1],16)
        source={record_base+i*56:struct.unpack_from('<I',p,32+i*16)[0] for i in range(h[3])}
        def sample(seconds):
            end=time.monotonic()+seconds;seen=set()
            while time.monotonic()<end:
                write(0x800aaab4,3000)
                record=struct.unpack('<I',read(0x800a927c,4))[0]
                seen.add(source.get(record,record))
                time.sleep(.015)
            return seen
        sample(.5)
        results={}
        for name,buttons,expected in [('1',0x7fff,0x1a20b4),('2',0xefff,0x1aac64),
                                      ('3',0xbfff,0x1b96d0),('4',0xdfff,0x1c0fe8)]:
            q(dict(cmd='press',buttons=buttons,frames=3))
            seen=sample(1.3);results[name]=[f'{s:08x}' for s in sorted(seen)]
            assert expected in seen,(name,results[name])
        q(dict(cmd='input_route_clear'))
        for buttons,frames in ((0x7fff,2),(0xffff,2),(0xefff,2),(0xffff,90)):
            assert q(dict(cmd='input_route_append',buttons=buttons,frames=frames))['ok']
        q(dict(cmd='input_route_start'))
        seen=sample(2.2);results['1,2']=[f'{s:08x}' for s in sorted(seen)]
        assert 0x1a67b4 in seen,results['1,2']
        q(dict(cmd='screenshot',path=str(work/'jun-selector-smoke.png')))
        (work/'jun-selector-smoke.json').write_text(json.dumps(results,indent=2)+'\n')
        print('PASS Jun selection via kick confirmation; original 1/2/3/4 clips and 1,2 transition',flush=True)
    finally:
        subprocess.run(['taskkill','/PID',str(info['pid']),'/T','/F'],capture_output=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--only',choices=['jun','jin'])
    args=ap.parse_args()
    if args.only!='jun':check(False)
    if args.only!='jin':check(True)

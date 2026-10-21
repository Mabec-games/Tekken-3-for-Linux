"""Bounded live checks for the reported df1+2 recovery and Jin ff3 hit.

Position/dummy state are arranged; attack inputs, contact and recovery run
through the native engine. This is not a complete hard-CPU/movelist test.
"""
import argparse
import json
import re
import struct
import time
from pathlib import Path
from test_jun_roster import Session, cabinet
from test_jun_solo import Solo, P1, P2


class Reported(Solo):
    def __init__(self, opponent, receiving=False, p1_override=None):
        self.s = Session()
        try:
            cabinet(self.s, not receiving, 23 if receiving else opponent,p1_override)
        except BaseException:
            self.s.stop()
            raise
        self.s.write(P2+0xc5, 0, 1)
        time.sleep(3)
        self.pack = (Path(self.s.info['assets'])/'Jun-TTT1-combat.jmv').read_bytes()
        self.count = struct.unpack_from('<I', self.pack, 12)[0]
        p = 2 if receiving else 1
        self.base = int(re.findall(rf'installed P{p} alias table,.*records=([0-9A-F]+)',
                                  Path(self.s.info['log']).read_text())[-1], 16)
        self.source = {self.base+i*56: struct.unpack_from('<I',self.pack,32+i*16)[0]
                       for i in range(self.count)}
        self.trace = []

    def route(self, steps):
        self.s.q(cmd='input_route_clear')
        for frames, buttons in steps:
            self.s.q(cmd='input_route_append',frames=frames,buttons=buttons)
        self.s.q(cmd='input_route_start')

    def recover(self):
        self.align(600)
        self.force(1, 6)  # Native ki charge: no neutral auto-guard.
        self.route([(3,0xff9f),(3,0x6f9f),(180,0xffff)])
        rows = self.sample(3)
        damage = 130-min(b['hp'] for a,b in rows)
        assert damage>0, ('df1+2 did not connect',rows[-1])
        # Let the actual CPU get up and attack, watching both damage and
        # imported-record ownership. Do not force its recovery transition.
        self.s.q(cmd='set_input',buttons=0xffff)
        self.s.write(P2+0xc5,1,1)
        rows += self.sample(5)
        native_attacks = []
        bad = []
        for a,b in rows:
            if b['clip']:
                index=(b['record']-self.base)//56
                rp=struct.unpack_from('<I',self.pack,40+index*16)[0]
                # Victim reactions carry no attacking-limb descriptor.
                if struct.unpack_from('<I',self.pack,rp+40)[0]:
                    bad.append((hex(b['clip']),b['frame']))
            elif b['record']:
                native_attacks.append(hex(b['record']))
        assert not bad, ('Opponent executed an imported attacking record',bad)
        self.s.shot('reported-df12-recovery')
        return dict(damage=damage, jun_damage=130-min(a['hp'] for a,b in rows),
                    native_records=sorted(set(native_attacks)),
                    imported_victim_clips=sorted({hex(b['clip']) for a,b in rows if b['clip']}),
                    jun_clips=sorted({hex(a['clip']) for a,b in rows if a['clip']}))

    def receiving_hit(self, gon=False):
        self.align(200 if gon else 700)
        self.force(1,6 if gon else 0xd67)  # Non-guarding dummy, feet down for the low.
        self.route([(4,0xffbf),(3,0xdfbf),(180,0xffff)] if gon else
                   [(3,0xffdf),(2,0xffff),(3,0xbfdf),(180,0xffff)])
        rows=self.sample(3)
        damaged=[b for a,b in rows if b['hp']<130]
        assert damaged, 'Requested attack did not connect'
        native=[b for b in damaged if 0x80010000<=b['record']<0x80200000]
        assert native, ('Hit never entered a native reaction',damaged[:2])
        assert rows[-1][1]['clip']==0x102b58, 'Jun did not recover to her own idle'
        self.s.shot('reported-'+('gon-d4' if gon else 'jin-ff3')+'-recovery')
        return dict(damage=130-min(b['hp'] for b in damaged),
                    attacker_records=sorted({hex(a['record']) for a,b in rows}),
                    native_reactions=sorted({hex(b['record']) for b in native}))


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--case',choices=('heihachi','ogre','jin-ff3','gon-d4'),required=True)
    args=ap.parse_args()
    receiving=args.case in ('jin-ff3','gon-d4')
    f=Reported(13 if args.case=='heihachi' else 20,receiving,17 if args.case=='gon-d4' else None)
    result=None
    try:
        result=f.receiving_hit(args.case=='gon-d4') if receiving else f.recover()
        print('PASS',args.case,result,flush=True)
    finally:
        (f.s.work/f'reported-{args.case}.json').write_text(json.dumps(
            dict(result=result,trace=f.trace,session=f.s.info),indent=2))
        f.s.stop()

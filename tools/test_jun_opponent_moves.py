"""Live regression for native opponents inheriting Jun's recovery move graph.

Uses an isolated game with AI disabled. Jun's throw is started through the
native transition queue; contact, victim animation, damage and recovery run
in the game. --case crouch starts a legal imported hit-reaction fixture and
uses real pad input to crouch-cancel it and attack.
"""
import argparse
import json
import re
import struct
import time
from pathlib import Path

from test_jun_roster import Session, cabinet
from test_jun_solo import Solo, P1, P2


class OpponentMoves(Solo):
    def __init__(self, jun_player=1):
        self.s = Session()
        self.jun_player = jun_player
        self.victim = 1-jun_player
        cabinet(self.s, jun_player == 0, 9 if jun_player == 0 else 23)
        self.s.write(P2+0xc5, 0, 1)
        time.sleep(3)
        self.pack = (Path(self.s.info['assets'])/'Jun-TTT1-combat.jmv').read_bytes()
        self.count = struct.unpack_from('<I', self.pack, 12)[0]
        log = Path(self.s.info['log']).read_text()
        self.base = int(re.findall(
            rf'installed P{jun_player+1} alias table,.*records=([0-9A-F]+)', log)[-1], 16)
        self.source = {self.base+i*56: struct.unpack_from('<I', self.pack, 32+i*16)[0]
                       for i in range(self.count)}
        self.trace = []

    def index(self, clip):
        return next(i for i in range(self.count) if self.source[self.base+i*56] == clip)

    def native(self, alias):
        table = self.s.value(self.s.value(0x800adc20+self.victim*4)+12)
        return self.s.value(table+alias*4)

    def throw_recovery(self):
        self.approach()
        if self.jun_player == 0:
            self.s.q(cmd='press', buttons=0x3fff, frames=3)
        else:
            self.force(1, 8192+self.index(0x62dcc4), 14)
        expected = self.native(0x99)  # Face-up down state after this throw.
        paired = False
        end = time.monotonic()+9
        while time.monotonic() < end:
            row = self.state()
            jun, other = row[self.jun_player], row[self.victim]
            if jun['throw'] > 0 and other['throw'] < 0:
                paired = True
                assert (jun['clip'], other['clip']) == (0x757e64, 0x759d84)
            if paired and other['clip'] != 0x759d84:
                self.s.shot(f'opponent-recovery-p{self.victim+1}')
                assert other['hp'] == 100, ('Wrong throw damage', other)
                assert other['record'] == expected, (
                    'Opponent inherited Jun recovery and its attack links', other, hex(expected))
                return dict(paired=True, damage=30, native_recovery=hex(expected))
            time.sleep(.008)
        raise AssertionError('Throw did not reach recovery')

    def crouch_cancel(self):
        assert self.victim == 0, 'This input fixture uses the first controller'
        self.align(4000)
        # Arcade hit reaction 80075ED4 permits crouch input from frame 9.
        i = next(i for i in range(self.count)
                 if struct.unpack_from('<I', self.pack, 36+i*16)[0] == 0x80075ed4)
        a = P1
        self.s.write(a+0xc3, 0, 1)
        for off, value in ((0x6e, 0), (0x198, 1), (0x19a, 6), (0x1a0, 8192+i)):
            self.s.write(a+off, value, 2)
        self.s.write(a+0x1a4, self.base+i*56)
        self.s.q(cmd='set_input', buttons=0xffbf)
        self.s.write(a+0xc3, 1, 1)
        self.sample(.6)
        self.s.q(cmd='set_input', buttons=0xbfbf)  # d+3 through the real pad.
        rows = self.sample(1.2)
        self.s.q(cmd='clear_input')
        self.s.shot('opponent-crouch-attack')
        copied = sorted({hex(row[0]['clip']) for row in rows if row[0]['clip']})
        assert not copied, ('Native opponent performed imported Jun moves', copied)
        assert any(row[0]['record'] != self.native(3) for row in rows)
        return dict(native_attack_records=sorted({hex(row[0]['record']) for row in rows}))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', choices=('throw', 'crouch'), required=True)
    ap.add_argument('--jun-player', type=int, choices=(1, 2), default=2)
    ap.add_argument('--label', default='fixed')
    args = ap.parse_args()
    f = OpponentMoves(args.jun_player-1)
    result = None
    try:
        result = f.throw_recovery() if args.case == 'throw' else f.crouch_cancel()
        print('PASS', args.case, f'Jun P{args.jun_player}', result, flush=True)
    finally:
        out = f.s.work/f'opponent-moves-{args.case}-p{args.jun_player}-{args.label}.json'
        out.write_text(json.dumps(dict(result=result, trace=f.trace, session=f.s.info), indent=2))
        f.s.stop()


if __name__ == '__main__':
    main()

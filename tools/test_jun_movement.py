"""Live pad-input audit of Jun jumps and basic attacks in an isolated match."""
import json
import time
from test_jun_solo import Solo, P1


def run(f):
    results = {}
    for name, buttons in (('up', 0xffef), ('forward_jump', 0xffcf),
                          ('back_jump', 0xff6f), ('jab', 0x7fff),
                          ('right_punch', 0xefff), ('left_kick', 0xbfff),
                          ('right_kick', 0xdfff), ('df1+2', 0x6f9f),
                          ('3+4', 0x9fff)):
        f.force(0, 3)
        f.force(1, 3)
        f.align(1800)
        before = f.state()[0]
        f.s.q(cmd='press', buttons=buttons, frames=18 if 'jump' in name or name == 'up' else 3)
        rows = f.sample(.35)
        if 'jump' in name or name == 'up':
            f.s.shot('movement-' + name + '-airborne')
        rows += f.sample(1.65)
        a = [row[0] for row in rows]
        result = dict(start=before['position'], end=a[-1]['position'],
                      dx=a[-1]['position'][0]-before['position'][0],
                      x_range=[min(row['position'][0] for row in a), max(row['position'][0] for row in a)],
                      min_y=min(row['position'][1] for row in a),
                      clips=sorted({hex(row['clip']) for row in a}),
                      recovered=a[-1]['clip'] == 0x102b58)
        results[name] = result
        print(name, result, flush=True)
        if 'jump' in name or name == 'up':
            f.s.shot('movement-' + name)
    return results


if __name__ == '__main__':
    f = Solo()
    result = None
    try:
        result = run(f)
    finally:
        (f.s.work / 'movement-audit.json').write_text(json.dumps(
            dict(result=result, trace=f.trace, session=f.s.info), indent=2))
        f.s.stop()

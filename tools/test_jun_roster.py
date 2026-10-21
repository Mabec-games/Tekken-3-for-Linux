#!/usr/bin/env python3
"""Isolated native roster integration checks using private local assets."""
import argparse,json,re,struct,subprocess,time
from pathlib import Path
from launch_jun_preview import ROOT,launch,debug_client

class Session:
    def __init__(self,visible=False):
        self.work=ROOT/'workspace/jun-import'
        self.visible=visible
        self.info=launch(ROOT/'build-debug-server-lite',self.work,headless=not visible,selector=True,roster=True,muted=True)
        self.loading_captured=False
    def q(self,**r):
        result=debug_client.query('127.0.0.1',self.info['port'],r)
        if result.get('ok') is False:raise RuntimeError((r,result))
        return result
    def read(self,a,n=4):
        result=self.q(cmd='read_ram',addr=f'{a:08x}',len=n)
        if 'hex' not in result:raise RuntimeError(result)
        return bytes.fromhex(result['hex'])
    def value(self,a,n=4):return int.from_bytes(self.read(a,n),'little')
    def write(self,a,v,n=4):
        for j in range(n):assert self.q(cmd='write_ram',addr=f'{a+j:08x}',val=f'{v>>(j*8)&255:02x}')['ok']
    def press(self,b):
        self.q(cmd='set_input',buttons=b);time.sleep(.16)
        self.q(cmd='set_input',buttons=65535);time.sleep(.16)
    def wait(self,predicate,description,seconds=35):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if predicate():return
            time.sleep(.06)
        raise AssertionError(description)
    def shot(self,name):
        path=self.work/(name+'.png')
        self.q(cmd='screenshot',path=str(path))
        if self.visible:
            assert self.q(cmd='ws_nw')['nw_extra']>0,'Visible test did not engage widescreen'
            assert struct.unpack_from('>I',path.read_bytes(),16)[0]>368,'Capture missed widescreen'
    def fonts(self):
        stock=(self.work/'ps1-slot7-vram.bin').read_bytes()
        for y in (0,128):
            words=self.q(cmd='vram_peek',x=896,y=y,w=48,h=128)['hex']
            actual=b''.join(struct.pack('<H',int(words[i:i+4],16)) for i in range(0,len(words),4))
            expected=b''.join(stock[row*2048+1792:row*2048+1888] for row in range(y,y+128))
            assert actual==expected,'Jun overwrote the native font atlas'
    def stop(self):subprocess.run(['taskkill','/PID',str(self.info['pid']),'/T','/F'],capture_output=True)
    def effects(self):
        stock=(self.work/'ps1-slot7-vram.bin').read_bytes()
        # Native blue guard spark: index 15 must stay transparent. The Jun
        # loading thumbnail previously replaced this CLUT with skin colors.
        expected=stock[503*2048+64*2:503*2048+80*2]
        def restored():
            h=self.q(cmd='vram_peek',x=64,y=503,w=16,h=1)['hex']
            actual=b''.join(struct.pack('<H',int(h[i:i+4],16)) for i in range(0,len(h),4))
            return actual==expected
        self.wait(restored,'Jun loading artwork corrupted the guard effect palette',2)
    def actor(self,p):
        return struct.unpack('<5H',self.read(0x800a923c+p*0x188c,10))
    def fight(self,p,cid):
        def ready():
            mode=self.value(0x800ae204)
            if mode==11 and self.value(0x800ae224,2)==2 and not self.loading_captured:
                self.shot('roster-loading-'+str(self.value(0x800afa88)))
                self.loading_captured=True
            if mode!=8 or self.value(0x800ae224,2)<6 or self.actor(p)[2]!=cid:return False
            base=self.value(0x8009bd28+p*4)
            moves=self.value(0x800adc20+p*4)
            record=self.value(0x800a927c+p*0x188c)
            return ((0x9f000000<=moves<0x9f100000 and 0x9f000000<=record<0x9f100000)
                    if cid==23 else 0x80100000<=base<0x80200000 and record!=0)
        self.wait(ready,f'P{p+1} character {cid} did not reach the native fight')
        identity=self.actor(p)
        assert identity[2]==cid,identity
        # Native moveset keys can differ for console additions/variants.
        if cid in (9,23,20):
            assert identity[1]==(14 if cid==20 else cid),identity
        if cid in (9,23):
            assert identity[4]==(52 if cid==23 else 18),identity
        if cid==23:
            header=self.value(0x800adc20+p*4)
            assert self.value(header+1,1)==23
            radii=[self.value(0x800a9228+p*0x188c+0x218+i*20,2) for i in range(14)]
            assert radii==[200,200,120,120,300,300,100,100,250,300,300,200,400,400],radii
            self.accessories(p)
        self.fonts()
        self.effects()
        return identity

    def accessories(self,p=0):
        # Check after native animation updates, which used to erase these
        # rotations even though the uploaded hair textures remained correct.
        expected={19:(-157,0,4093,0,4096,0,-4093,0,-157,-80,0,114),
                  20:(2029,2207,2790,-3184,-312,2560,1591,-3437,1561,79,-57,229)}
        for bone,matrix in expected.items():
            actual=struct.unpack('<9h2x3i',self.read(0x800a9228+p*0x188c+0xf74+bone*32,32))
            assert actual==matrix,(p,bone,actual)

def cabinet(s,jun=True,opponent=None,p1_override=None):
    rows=s.read(0x801296c8,22*12)
    ids=[struct.unpack_from('<H',rows,i*12+6)[0] for i in range(22)]
    assert len(set(ids))==22 and set(ids)==set(range(21))|{23},ids
    assert s.value(0x80118648)==22
    for _ in range(23):
        if s.value(0x80118668)==(23 if jun else 9):break
        s.press(0xff7f if jun else 0xffdf)
    else:raise AssertionError('Cabinet navigation did not reach target')
    s.shot('roster-cabinet-jun' if jun else 'roster-cabinet-jin')
    s.fonts()
    s.press(0x7fff)
    if opponent is not None:
        # Arrange a deterministic opponent during the native loading phase;
        # selection/navigation above remain actual player-input checks.
        s.wait(lambda:s.value(0x800ae204)==11,'Loading screen not reached',15)
        s.write(0x800add5e,opponent,2);s.write(0x800add9a,0,2)
        if p1_override is not None:
            s.write(0x800add5c,p1_override,2)
    identity=s.fight(0,p1_override if p1_override is not None else 23 if jun else 9)
    if opponent is not None:
        s.fight(1,opponent)
        if jun:
            h1,h2=s.value(0x800adc20),s.value(0x800adc24)
            assert h1!=h2 and s.value(h1+12)!=s.value(h2+12),'Mirror actors share combat tables'
        elif p1_override is None:
            h1=s.value(0x800adc20)
            assert s.value(h1+1,1)==9 and s.value(h1+12)<0x80200000,'Jin inherited Jun combat data'
    s.shot('roster-fight-'+('jun' if jun else 'jin')+('-vs-jun' if opponent==23 else ''))
    return identity

def body_collision(s):
    """Walk into the opponent through actual inputs and native separation."""
    s.write(0x800aaab4+0xc5,0,1)
    time.sleep(3)  # Finish the native intro before applying movement.
    for p,x in enumerate((-1600,1600)):
        a=0x800a9228+p*0x188c
        s.write(a,x);s.write(a+8,0)
        if s.actor(p)[2]==23:
            radii=[s.value(a+0x330+i*16,2) for i in range(8)]
            assert radii==[240,96,96,300,120,120,120,120],radii
    history=[]
    s.q(cmd='set_input',buttons=0xffdf)
    try:
        end=time.monotonic()+3
        while time.monotonic()<end:
            x1=struct.unpack('<i',s.read(0x800a9228))[0]
            x2=struct.unpack('<i',s.read(0x800aaab4))[0]
            history.append((x1,x2))
            assert x2>x1,('Fighters walked through one another',x1,x2)
            time.sleep(.03)
    finally:s.q(cmd='clear_input')
    assert history[-1][0]>0 and history[-1][1]>2000,history[-1]
    return dict(minimum_separation=min(b-a for a,b in history),final_positions=history[-1])

def attacks(s,p=0):
    # This fixture checks input transitions with an idle opponent. Damage
    # reception is exercised separately with the real CPU opponent enabled.
    s.write(0x800aaab4+0xc5,0,1)
    pack=(Path(s.info['assets'])/'Jun-TTT1-combat.jmv').read_bytes()
    count=struct.unpack_from('<I',pack,12)[0]
    log=Path(s.info['log']).read_text()
    base=int(re.findall(rf'installed P{p+1} alias table,.*records=([0-9A-F]+)',log)[-1],16)
    source={base+i*56:struct.unpack_from('<I',pack,32+i*16)[0] for i in range(count)}
    def sample(seconds):
        seen=set();end=time.monotonic()+seconds
        while time.monotonic()<end:
            s.write(0x800aaab4,3000)
            rec=s.value(0x800a927c+p*0x188c);seen.add(source.get(rec,rec));time.sleep(.01)
        return seen
    # Wait for control, not a wall-clock guess that can still hit the intro.
    s.wait(lambda: source.get(s.value(0x800a927c+p*0x188c))==0x102b58,
           'Jun intro did not reach neutral',8)
    results={}
    for name,button,expected in [('1',0x7fff,0x1a20b4),('2',0xefff,0x1aac64),('3',0xbfff,0x1b96d0),('4',0xdfff,0x1c0fe8)]:
        s.q(cmd='press',buttons=button,frames=3)
        seen=sample(1.4);assert expected in seen,(name,[hex(x) for x in seen]);results[name]=hex(expected)
    return results

def team(s):
    s.write(0x800afa88,2);s.write(0x800ae224,0,2);s.write(0x800ae204,10,2)
    time.sleep(1.2)
    s.press(0x7fff)
    state=0x800b8d70
    for _ in range(16):
        x,y=s.value(state+8),s.value(state+12)
        if (x,y)==(5,2):break
        s.press(0xffbf if y<2 else 0xffdf)
    else:raise AssertionError('Team grid did not reach Jun')
    s.shot('roster-team-jun')
    s.fonts()
    s.press(0x7fff)
    assert s.value(state+44)==1 and s.value(state+56)==92
    s.shot('roster-team-confirmed')
    identity=s.fight(0,23)
    s.shot('roster-team-fight')
    return identity

def receive_hit(s):
    before=s.value(0x800a961c)
    s.wait(lambda:s.value(0x800a961c)<before,'Jun took no damage from opponent attacks',30)
    after=s.value(0x800a961c)
    s.shot('roster-jun-received-hit')
    return dict(hp_before=before/65536,hp_after=after/65536)

def jab_damage(s):
    s.write(0x800aaab4+0xc5,0,1)
    time.sleep(3)  # Let the original Jun intro finish before sending input.
    s.q(cmd='set_input',buttons=0xffdf)
    try:
        def in_range():
            a=struct.unpack('<3i',s.read(0x800a9228,12))
            b=struct.unpack('<3i',s.read(0x800aaab4,12))
            return (a[0]-b[0])**2+(a[2]-b[2])**2<1250**2
        s.wait(in_range,'Could not walk into jab range',6)
        time.sleep(.8)  # Reach body-contact distance, inside the short jab.
    finally:s.q(cmd='clear_input')
    time.sleep(.05)
    # Native neutral automatically guards a high jab. Put the dummy into a
    # non-attacking victory animation so this measures normal damage, without
    # a guard or the counter-hit bonus introduced by a ki-charge fixture.
    dummy=0x800aaab4;alias=0xd67
    table=s.value(s.value(0x800adc24)+12)
    s.write(dummy+0xc3,0,1)
    for offset,value in ((0x6e,0),(0x198,1),(0x19a,6),(0x19c,0),(0x19e,0),(0x1a0,alias)):
        s.write(dummy+offset,value,2)
    s.write(dummy+0x1a4,s.value(table+alias*4));s.write(dummy+0xc3,1,1)
    time.sleep(.06)
    before=s.value(0x800aaab4+0x3f4)
    s.q(cmd='press',buttons=0x7fff,frames=3)
    s.wait(lambda:s.value(0x800aaab4+0x3f4)<before,'Jun jab did not contact Jin',3)
    after=s.value(0x800aaab4+0x3f4)
    # Jun's original base damage is 4. The native collision result identifies
    # the struck body zone, whose percentage is applied by 80045038. A raised
    # arm in this dummy pose can take 130%, so the resulting loss is 5 HP.
    contacts=[s.read(dummy+offset,44) for offset in (0x13c,0x168)]
    contacts=[row for row in contacts if any(row[:24])]
    assert len(contacts)==1,contacts
    body_zone=struct.unpack_from('<H',contacts[0],24)[0]
    assert body_zone<14,body_zone
    percentage=s.value(0x8001deec+body_zone*2,2)
    assert not any(s.value(dummy+offset,1) for offset in (0xcf,0xd3,0xd4)),'Fixture added guard/counter/range modifiers'
    expected=4*percentage//100
    assert before-after==expected*65536,(before,after,body_zone,percentage)
    s.shot('roster-jun-jab-hit')
    return dict(hp_before=before/65536,hp_after=after/65536,base_damage=4,
                body_zone=body_zone,zone_percentage=percentage,damage=expected)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',choices=['jun','jin','team','p2','mirror','hit','jab','push','push-p2'],required=True)
    ap.add_argument('--visible',action='store_true',help='Verify the real widescreen frontend and captures')
    a=ap.parse_args();s=Session(a.visible)
    try:
        if a.case=='team':result=team(s)
        else:
            result=cabinet(s,a.case not in ('jin','p2','push-p2'),23 if a.case in ('p2','mirror','push-p2') else 9 if a.case in ('jab','push') else None)
            if a.case=='jun':result=dict(identity=result,attacks=attacks(s))
            if a.case=='hit':result=dict(identity=result,damage=receive_hit(s))
            if a.case=='jab':result=dict(identity=result,damage=jab_damage(s))
            if a.case in ('push','push-p2'):result=dict(identity=result,collision=body_collision(s))
        (s.work/f'roster-test-{a.case}.json').write_text(json.dumps(dict(case=a.case,result=result,session=s.info),indent=2)+'\n')
        print('PASS',a.case,result,flush=True)
    finally:s.stop()

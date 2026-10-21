"""Private live costume regression: native selection, VRAM, accessories, mirrors.

Run --case gallery --renderer opengl for the actual inline L1 carousel input path.
All fixtures use isolated executables, saves and muted audio.
"""
import argparse
import json
import re
import struct
import time
from pathlib import Path
from launch_jun_preview import ROOT, launch
from test_jun_roster import Session, jab_damage
from plan_jun_texture_atlas import inspect as inspect_atlas, pack as pack_atlas


class Costumes(Session):
    def __init__(self, renderer):
        self.work=ROOT/'workspace/jun-import'
        self.visible=renderer=='opengl'
        self.info=launch(ROOT/'build-debug-server-lite',self.work,
                         headless=not self.visible,selector=True,roster=True,
                         muted=True,renderer=renderer)
        self.loading_captured=False
        self.output=self.work/'outfit-research'
        self.output.mkdir(exist_ok=True)

    def select(self, outfit, opponent=9, opponent_outfit=0, gallery=False):
        self.q(cmd='clear_input')
        self.q(cmd='savestate',op='load',slot=7)
        time.sleep(.4)
        for _ in range(24):
            if self.value(0x80118668)==23:break
            self.press(0xff7f)
        else:raise AssertionError('Jun tile not reached')
        self.press(0x7fff) # Character first; no native costume is committed yet.
        if gallery:
            v=self.q(cmd='outfit_slots')
            assert v['menu']==-1 and v['players'][0]['count']==3,v
            before=self.value(0x8011863c)
            time.sleep(.2)
            assert self.value(0x8011863c)<before,'Carousel paused the native countdown'
        for _ in range(3):
            if self.q(cmd='outfit_slots')['players'][0]['index']==outfit:break
            self.press(0xffdf)
        assert self.q(cmd='outfit_slots')['players'][0]['index']==outfit
        if gallery:
            self.q(cmd='outfit_screenshot',path=str(self.output/f'gallery-{outfit+1}.png'))
        self.press(0xbfff)
        self.wait(lambda:self.value(0x800ae204)==11,'Native loading screen',15)
        self.write(0x800add5e,opponent,2)
        self.write(0x800add9a,opponent_outfit,2)
        self.ready(outfit,opponent,opponent_outfit)

    def ready(self,outfit,opponent,other):
        self.wait(lambda:self.value(0x800ae204)==8 and self.value(0x800ae224,2)>=8,
                  'Native fight initialization',40)
        self.write(0x800aaab4+0xc5,0,1)
        time.sleep(3)
        self.check_actor(0,outfit)
        if opponent==23:self.check_actor(1,other)
        else:assert self.actor(1)[2]==9
        self.fonts();self.effects()

    def check_actor(self,player,outfit):
        identity=self.actor(player)
        assert identity[:3]==(92+outfit,23,23),identity
        assert identity[4]==52+outfit,identity
        base=self.value(0x8009bd28+player*4)
        model=int(re.findall(rf'Jun outfit {outfit+1}: model=([0-9A-F]+)',
                             Path(self.info['log']).read_text())[-1],16)
        assert self.value(base+24)==model+0x6c8
        actor=0x800a9228+player*0x188c
        expected=({19,20},{19},{19,20,21})[outfit]
        for i in range(19,23):
            part=actor+0x4f0+i*40
            assert bool(self.value(part))==(i in expected),(outfit,i)
            if i not in expected:continue
            row=self.value(0x8001a05c+i,1)
            parent=self.value(base+24+row*56+24)
            assert self.value(actor+0x8f4+i*68+64)==self.value(actor+0x4f4+parent*40)
            assert self.read(actor+0xf88+i*32,12)==self.read(base+24+row*56+12,12)
        assert 0x9f000000<=self.value(0x800adc20+player*4)<0xa0000000
        return dict(identity=identity,header=hex(base),model=hex(model),accessories=sorted(expected))

    def vram(self,x,y,w,h):
        if w>128:
            return b''.join(self.vram(x+offset,y+row,min(128,w-offset),1)
                            for row in range(h) for offset in range(0,w,128))
        raw=self.q(cmd='vram_peek',x=x,y=y,w=w,h=h)['hex']
        return b''.join(struct.pack('<H',int(raw[i:i+4],16)) for i in range(0,len(raw),4))

    def textures(self,player,outfit):
        layout=pack_atlas(inspect_atlas(outfit+1)[0])
        data=(self.work/f'jun/Jun-TTT1-arcade-P{outfit+1}.tim').read_bytes()
        images=[];palettes=bytearray(1024);palette_mask=bytearray(1024);o=0
        source_face=None
        while o+8<len(data):
            magic,flags=struct.unpack_from('<II',data,o);assert magic==16;o+=8
            n,x,y,w,h=struct.unpack_from('<I4H',data,o)
            for row in range(h):
                start=(y+row)*512+x*2
                palettes[start:start+w*2]=data[o+12+row*w*2:o+12+(row+1)*w*2]
                palette_mask[start:start+w*2]=bytes([1])*w*2
            o+=n
            n,x,y,w,h=struct.unpack_from('<I4H',data,o)
            pixels=data[o+12:o+n]
            if x==0 and y==0:source_face=pixels
            images.append((x,y,w,h,flags&3,pixels));o+=n
        actual=self.vram(0,504+player*4,256,2)
        differences=[(i,a,b) for i,(a,b,m) in enumerate(zip(actual,palettes,palette_mask)) if m and a!=b]
        assert not differences,('palette',player,outfit,differences[:30])
        for x,y,w,h,mode,pixels in images:
            tile=next(t for t in layout if (t['x'],t['y'],t['w'],t['h'],t['mode'])==(x,y,w,h,mode))
            live=self.vram(384+tile['dx'],player*256+tile['dy'],w,h)
            if live!=pixels and not (x==16 and y==64 and live==source_face):
                (self.output/f'failed-tile-{player}-{outfit}-{x}-{y}.bin').write_bytes(live)
                self.shot(f'outfit-research/failed-tile-{player}-{outfit}')
                raise AssertionError(('tile',player,outfit,x,y,len(live),[(i,a,b) for i,(a,b) in enumerate(zip(live,pixels)) if a!=b][:16]))
        return len(images)

    def team_select(self,outfit):
        self.q(cmd='clear_input');self.q(cmd='savestate',op='load',slot=7);time.sleep(.3)
        self.write(0x800afa88,2);self.write(0x800ae224,0,2);self.write(0x800ae204,10,2)
        time.sleep(1.2);self.press(0x7fff)
        state=0x800b8d70
        for _ in range(16):
            x,y=self.value(state+8),self.value(state+12)
            if (x,y)==(5,2):break
            self.press(0xffbf if y<2 else 0xffdf)
        else:raise AssertionError('Team grid did not reach Jun')
        self.press(0x7fff)
        for _ in range(3):
            if self.q(cmd='outfit_slots')['players'][0]['index']==outfit:break
            self.press(0xffdf)
        assert self.q(cmd='outfit_slots')['players'][0]['index']==outfit
        self.press(0xbfff)
        assert self.value(state+44)==1 and self.value(state+56)==92+outfit
        self.wait(lambda:self.value(0x800ae204)==11,'Team native loading',15)
        self.write(0x800add5e,9,2);self.write(0x800add9a,0,2)
        self.ready(outfit,9,0)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',choices=('direct','mirror','team','gallery'),required=True)
    ap.add_argument('--renderer',choices=('software','opengl'),default='software')
    a=ap.parse_args();s=Costumes(a.renderer);results=[]
    try:
        for outfit in range(3):
            if a.case=='team':s.team_select(outfit)
            else:s.select(outfit,23 if a.case=='mirror' else 9,(outfit+1)%3,a.case=='gallery')
            row=dict(outfit=outfit+1,player1=s.check_actor(0,outfit),tiles1=s.textures(0,outfit))
            if a.case=='mirror':
                other=(outfit+1)%3
                row.update(player2=s.check_actor(1,other),tiles2=s.textures(1,other))
                assert s.value(0x8009bd28)!=s.value(0x8009bd2c),'Mixed outfits share a native header'
                assert s.value(0x800adc20)!=s.value(0x800adc24),'Mirror combat tables shared'
            s.shot(f'outfit-research/{a.case}-{a.renderer}-{outfit+1}')
            if a.case=='direct':row['jab']=jab_damage(s)
            results.append(row)
            print('PASS',a.case,a.renderer,'outfit',outfit+1,flush=True)
        (s.output/f'{a.case}-{a.renderer}-validation.json').write_text(json.dumps(dict(results=results,session=s.info),indent=2)+'\n')
    finally:s.stop()


if __name__=='__main__':main()

"""Cold-boot practice UI investigation. Never loads or writes a save state."""
import argparse
import json
import time
from pathlib import Path
from launch_jun_preview import ROOT, launch
from test_jun_roster import Session


class PracticeSession(Session):
    def shot(self,name):
        # Native practice menus may deliberately retain their 4:3 panel;
        # do not impose the cabinet selector's widened-layout assertion.
        self.q(cmd='screenshot',path=str(self.work/(name+'.png')))


def press(s, buttons):
    s.q(cmd='set_input',buttons=hex(buttons))
    time.sleep(.12)
    s.q(cmd='set_input',buttons='0xffff')
    time.sleep(.18)


def boot(s):
    end=time.monotonic()+40
    while time.monotonic()<end:
        screen=s.value(0x800ae204)
        if screen==4:
            time.sleep(.6)
            print('MAIN MENU',s.value(0x800ae224),flush=True)
            return
        press(s,0xfff7)
    raise AssertionError('Cold boot did not reach the main menu')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--character',choices=('jun','jin'),default='jun')
    ap.add_argument('--visible',action='store_true')
    ap.add_argument('--label',default='check')
    ap.add_argument('--outfit',type=int,choices=(1,2,3),default=1)
    ap.add_argument('--opponent-outfit',type=int,choices=(1,2,3),default=1)
    ap.add_argument('--renderer',choices=('software','opengl'),default='software')
    ap.add_argument('--baseline',type=Path,help='Native cold-boot UI region JSON for exact comparison')
    args=ap.parse_args()
    s=PracticeSession.__new__(PracticeSession)
    s.work=ROOT/'workspace/jun-import'
    s.visible=args.visible
    s.loading_captured=False
    s.info=launch(ROOT/'build-debug-server-lite',s.work,headless=not args.visible,
                  selector=True,roster=True,muted=True,cold_boot=True,renderer=args.renderer)
    (s.work/'practice-cold-session.json').write_text(json.dumps(s.info,indent=2))
    print(json.dumps(s.info),flush=True)
    boot(s)
    # The stock menu has Practice two entries above Arcade.
    press(s,0xffef);press(s,0xffef)
    s.shot('practice-cold-mode')
    press(s,0x7fff)
    s.wait(lambda:s.value(0x800ae204)==9 and s.value(0x80118648)==22,
           'Practice selector did not initialize')
    print('SELECTOR mode',s.value(0x800afa88),flush=True)
    assert s.value(0x800afa88)==5, 'Did not select Practice'
    wanted=23 if args.character=='jun' else 9
    for _ in range(23):
        if s.value(0x80118668)==wanted:break
        press(s,0xff7f)
    assert s.value(0x80118668)==wanted
    press(s,(0x7fff,0xbfff,0xfff7)[args.outfit-1])
    time.sleep(.5)
    s.shot('practice-cold-opponent')
    press(s,(0x7fff,0xbfff,0xfff7)[args.opponent_outfit-1])
    s.wait(lambda:s.value(0x800ae204)==8 and s.value(0x800ae224,2)>=6,
           'Practice fight did not start')
    time.sleep(5)  # Native intros must finish before the practice menu accepts input.
    s.shot('practice-cold-'+args.character)
    print('PRACTICE ready',s.actor(0),s.actor(1),flush=True)
    press(s,0x7fff)  # Freestyle -> settings.
    s.shot('practice-settings-'+args.character+'-'+args.label)
    press(s,0xffbf);press(s,0x7fff)  # Command List.
    time.sleep(.3)
    prefix='practice-command-'+args.character+'-'+args.label
    s.shot(prefix)
    regions={}
    for name,x,y,w,h in (('icons',384,224,64,32),('font_cluts',384,507,64,1),
                          ('font',464,16,48,112)):
        regions[name]=s.q(cmd='vram_peek',x=x,y=y,w=w,h=h)['hex']
    (s.work/(prefix+'.json')).write_text(json.dumps(dict(session=s.info,regions=regions),indent=2))
    if args.baseline:
        baseline=json.loads(args.baseline.read_text())
        # The initial native capture included the face backup and HUD name;
        # compare only the command-list glyphs, excluding those dynamic tiles.
        if len(baseline['font'])==64*128*4:
            full=baseline['font']
            baseline['font']=''.join(full[(row*64+16)*4:(row*64+64)*4] for row in range(16,128))
        for name,raw in regions.items():
            assert raw==baseline[name], f'Native practice {name} changed'
        print('PASS native command icons, glyphs and font palettes',flush=True)
    assert 'savestate: LOADED' not in Path(s.info['log']).read_text(errors='replace')
    assert not list((Path(s.info['executable']).parent/'saves').rglob('*.pst'))
    if args.character=='jun':
        from test_jun_outfits import Costumes
        inspector=Costumes.__new__(Costumes)
        inspector.info=s.info;inspector.work=s.work;inspector.visible=False
        inspector.output=s.work/'outfit-research';inspector.output.mkdir(exist_ok=True)
        for player in (0,1):
            outfit=s.actor(player)[4]-52
            assert 0<=outfit<=2
            print('TEXTURES',player+1,outfit+1,inspector.textures(player,outfit),flush=True)
    s.q(cmd='clear_input')
    print('Left isolated cold-boot session open for UI inspection.',flush=True)


if __name__=='__main__':
    main()

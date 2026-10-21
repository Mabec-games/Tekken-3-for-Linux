"""Legacy filename: live inline-carousel regression via the runtime debug port."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'psxrecomp/tools'))
import debug_client as debug
ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=4373);ap.add_argument('--matches',action='store_true');args=ap.parse_args()
q=lambda r:debug.query('127.0.0.1',args.port,r)
out=Path('out/outfit-slots');out.mkdir(parents=True,exist_ok=True)
def tap(mask):
 q({'cmd':'set_input','buttons':f'{65535^mask:04X}'});time.sleep(.075)
 q({'cmd':'set_input','buttons':'FFFF'});time.sleep(.12)
def select(cid):
 q({'cmd':'outfit_slots','cancel':1});q({'cmd':'set_input','buttons':'FFFF'})
 q({'cmd':'savestate','op':'load','slot':7});time.sleep(.35)
 target=9 if cid==18 else 2 if cid==5 else 0
 row=[7,4,5,1,6,8,0,3,2,9]
 for _ in range(14):
  v=q({'cmd':'outfit_slots'})['players'][0]
  if v['character']==row[target]:break
  tap(0x20)
 else:raise AssertionError(v)
 if cid==18:tap(0x40)
 v=q({'cmd':'outfit_slots'})['players'][0];assert v['character']==cid,v
 tap(0x8000)
 v=q({'cmd':'outfit_slots'});assert v['menu']==-1,v
 return v
results=[]
try:
 select(5)
 before=int.from_bytes(bytes.fromhex(q({'cmd':'read_ram','addr':'8011863c','len':4})['hex']),'little')
 time.sleep(1.2)
 after=int.from_bytes(bytes.fromhex(q({'cmd':'read_ram','addr':'8011863c','len':4})['hex']),'little')
 assert after<before, 'Carousel paused the native selector'
 # Card wrap + held-Right edge suppression via actual controller path.
 initial=q({'cmd':'outfit_slots'})['players'][0]['index']
 tap(0x20);assert q({'cmd':'outfit_slots'})['players'][0]['index']==(initial+1)%3
 q({'cmd':'set_input','buttons':'FFDF'});time.sleep(.3)
 assert q({'cmd':'outfit_slots'})['players'][0]['index']==(initial+2)%3
 q({'cmd':'set_input','buttons':'FFFF'});time.sleep(.08)
 q({'cmd':'outfit_screenshot','path':str((out/'nina-gallery-preview.png').resolve())})
 q({'cmd':'outfit_slots','cancel':1})
 for cid,count,names in [(5,3,['purple','crimson','white']),(18,4,['red','blue','tiger','jessica']),(7,4,['red','blue','school','pink'])]:
  for index,name in enumerate(names):
   v=select(cid);assert v['players'][0]['count']==count,v
   for _ in range(count):
    v=q({'cmd':'outfit_slots'})['players'][0]
    if v['index']==index:break
    q({'cmd':'outfit_slots','direction':1})
   assert v['index']==index
   prefix=f'{cid}-{name}'
   q({'cmd':'outfit_screenshot','path':str((out/(prefix+'-gallery.png')).resolve())})
   q({'cmd':'outfit_slots','accept':1});time.sleep(.3)
   locked=q({'cmd':'outfit_slots'});assert locked['players'][0]['locked'],locked
   data=bytes.fromhex(q({'cmd':'read_ram','addr':'80000000','len':2097152})['hex'])
   (out/(prefix+'-confirm.bin')).write_bytes(data)
   results.append({'character':cid,'index':index,'name':name,'state':locked})
   q({'cmd':'clear_input'})
   if args.matches:
    time.sleep(16)
    q({'cmd':'screenshot','path':str((out/(prefix+'-match.png')).resolve())})
   print(prefix,'confirmed',flush=True)
 select(5);q({'cmd':'outfit_screenshot','path':str((out/'nina-gallery-preview.png').resolve())})
finally:
 q({'cmd':'clear_input'})
(out/'gallery-validation.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS: live selector countdown, two-step opening, Right edges, wrap, 11 costume confirmations and carousel captures; controls released.',flush=True)

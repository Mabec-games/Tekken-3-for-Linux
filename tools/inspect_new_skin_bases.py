"""Read-only disc extraction/contact sheets for the three requested skin bases."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image, ImageDraw
from bns_tool import load_us_table, open_bns_source
from tim_tool import scan_tims, decode_rgba
from arc_tool import parse_archive

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/'workspace/new-skins-20260920'
out.mkdir(exist_ok=True)
exe = (ROOT/'disc/SLUS_004.02').read_bytes()
def exe_at(address, length):
    start = address - 0x80010000 + 0x800
    return exe[start:start+length]
table, _, _ = load_us_table(ROOT/'disc/SLUS_004.02')
report = []
parser = argparse.ArgumentParser()
parser.add_argument('--characters', default='0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20')
args = parser.parse_args()
faces = Image.new('RGB', (7*150, 3*180), '#333333')
face_draw = ImageDraw.Draw(faces)
with open_bns_source(ROOT/'disc/Tekken 3 (USA) (Track 1).bin') as source:
    for cid in map(int,args.characters.split(',')):
        models = list(exe_at(0x800958c4+cid*4, 4))
        print('character', cid, 'models', models)
        for model in dict.fromkeys(models):
            record = 73+model*4
            if not 0 <= record < len(table):
                continue
            entry = table[record]
            raw = source.read_at(entry.offset, entry.size)
            tiles = scan_tims(raw)
            if not tiles: continue
            if model == models[0]:
                t = tiles[0]
                face = Image.frombytes('RGBA',(t.pixel_width,t.image.height),decode_rgba(raw,t)).resize((128,150),Image.Resampling.NEAREST)
                faces.paste(face, ((cid%7)*150,(cid//7)*180))
                face_draw.text(((cid%7)*150,(cid//7)*180+153),f'CID {cid} model {model}',fill='white')
            (out/f'{record:03}.arc').write_bytes(raw)
            body_member = parse_archive(raw).members[0]
            body_tiles = [(i,t) for i,t in enumerate(tiles)
                          if body_member.offset <= t.offset and t.end_offset <= body_member.end_offset]
            body_count = len(body_tiles)
            rows = (body_count + 5)//6
            sheet = Image.new('RGB', (1024, rows*190), '#333333')
            draw = ImageDraw.Draw(sheet)
            atlas = Image.new('RGBA', (1536,rows*256))
            for i, t in body_tiles:
                im = Image.frombytes('RGBA', (t.pixel_width,t.image.height), decode_rgba(raw,t))
                atlas.paste(im.resize((256,256),Image.Resampling.NEAREST), ((i%6)*256,(i//6)*256))
                im.thumbnail((158,158),Image.Resampling.NEAREST)
                # Enlarge small decoded texture tiles for inspection only.
                im = im.resize((158,158),Image.Resampling.NEAREST)
                x,y=(i%6)*170,(i//6)*190
                sheet.paste(im,(x,y),im)
                draw.text((x,y+160),f'{i}: {t.pixel_width}x{t.image.height} ({t.image.x},{t.image.y})',fill='white')
            sheet.save(out/f'{cid}-{model}-{record}-contact.png')
            atlas.save(out/f'{record:03}-source-atlas.png')
            report.append(dict(character=cid,model=model,record=record,sha256=hashlib.sha256(raw).hexdigest(),tiles=len(tiles)))
(out/'bases.json').write_text(json.dumps(report,indent=2)+'\n')
faces.save(out/'character-identities.png')
print(json.dumps(report,indent=2))

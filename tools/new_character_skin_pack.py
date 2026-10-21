"""Pack the three authored atlases, with exact costume guards and no disc writes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image
from bns_tool import load_us_table, open_bns_source
from nina_skin_pack import fnv
from tim_tool import scan_tims
from arc_tool import parse_archive

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    'eddy-monochrome': dict(name='eddy', character=8, model=16, record=137, rows=5,
        sha='7d8aaf027d240df1eb88106a57f8eaadc97f3a4f854700b5be3242eca6524725', count=58,
        selected=[2,5,6,8,9,10,12,13,15,18,19,20,22,24,26,27], remap={}),
    'julia-blue': dict(name='julia', character=10, model=20, record=153, rows=6,
        sha='0d1bd2a871bf6a3b368750ab107d420f0351d1554a202f7e6bf6f99fa2034594', count=61,
        selected=[7,8,11,12,13,14,15,20,21,22,26,28,30],
        # Reuse authored blue fabric for the lower panel and silver fringe for
        # the narrow boot fringe; don't sample the generator's unused hand cell.
        remap={26:11,30:22}),
    'heihachi-tiger-coat': dict(name='heihachi', character=13, model=27, record=181, rows=5,
        sha='78ab813705426ce237146a17ef778a9b766f60f297cb952ee1d831754ee7bf30', count=55,
        # v2 uses plain trousers/shoes and fine stripes. Tile 11 mixes skin
        # and cuff; leave it stock along with all face/hair/bare-skin tiles.
        art='authored-atlas-v2.png',
        selected=[2,4,8,9,10,12,13,14,15,16,17,18,20,23,25,26,27,28,29,30,31],
        # Extra body TIMs precede the face-animation ARC member. This model
        # has only 22 animation TIMs, not the assumed 30.
        # Reuse authored leather, trimmed tiger cloth and fur. Horizontal
        # coat hems sample the right-hand trim rotated onto their bottom edge.
        remap={25:23,26:20,27:20,28:18,29:20,30:20,31:13},
        bottom_trim=[26,29,30]),
}

def costume_tile_ids(raw, tiles):
    """Only the first ARC member is the body texture package."""
    member = parse_archive(raw).members[0]
    return {i for i,t in enumerate(tiles)
            if member.offset <= t.offset and t.end_offset <= member.end_offset}


def build(raw, spec, directory):
    if hashlib.sha256(raw).hexdigest() != spec['sha']:
        raise ValueError('Base does not match the verified SLUS-00402 costume')
    tiles = scan_tims(raw)
    if len(tiles) != spec['count']:
        raise ValueError('Unexpected base texture layout')
    body_ids = costume_tile_ids(raw, tiles)
    if len(set(spec['selected'])) != len(spec['selected']):
        raise ValueError('Duplicate costume tile')
    for tile_id in spec['selected']:
        if tile_id not in body_ids or tiles[tile_id].mode not in (0,1) or tiles[tile_id].clut is None:
            raise ValueError('Only indexed costume tiles in the body ARC member are allowed')
        if not 0 <= spec['remap'].get(tile_id,tile_id) < 6*spec['rows']:
            raise ValueError('Authored atlas cell is out of bounds')
    source = directory/spec.get('art', 'authored-atlas.png')
    with Image.open(source) as im:
        art = im.convert('RGBA')
    if abs(art.width/art.height - 6/spec['rows']) > .02 or min(art.size) < 1024:
        raise ValueError(f'{source}: expected 6 x {spec["rows"]} equal-cell atlas')
    cell, gutter, columns = 256, 16, 4
    stride = cell + gutter*2
    rows = (len(spec['selected'])+columns-1)//columns
    atlas = Image.new('RGBA', (columns*stride, rows*stride))
    for slot, tile_id in enumerate(spec['selected']):
        source_id = spec['remap'].get(tile_id, tile_id)
        x, y = source_id%6, source_id//6
        crop = art.crop((round(x*art.width/6), round(y*art.height/spec['rows']),
                         round((x+1)*art.width/6),round((y+1)*art.height/spec['rows'])))
        crop = crop.resize((cell,cell),Image.Resampling.LANCZOS)
        padded = np.pad(np.array(crop),((gutter,gutter),(gutter,gutter),(0,0)),mode='edge')
        atlas.paste(Image.fromarray(padded),((slot%columns)*stride,(slot//columns)*stride))
    atlas.save(directory/f'{spec["name"]}.png')
    (directory/f'{spec["name"]}.rgba').write_bytes(b'HDRGBA01'+struct.pack('<2I',*atlas.size)+atlas.tobytes())
    entries, report = [], []
    for player in (0,1):
        for slot, tile_id in enumerate(spec['selected']):
            t = tiles[tile_id]; q, c = t.image, t.clut
            x,y=384+q.x,player*256+q.y
            cx,cy=c.x,504+player*4+c.y
            pixel_hash=fnv(raw[q.data_offset:q.end_offset])
            clut_hash=fnv(raw[c.data_offset:c.end_offset])
            factor=2 if t.mode else 4
            sx=(cell-1)/((t.pixel_width-1)*atlas.width)
            sy=(cell-1)/((q.height-1)*atlas.height)
            ox=((slot%columns)*stride+gutter+.5)/atlas.width-x*factor*sx
            oy=((slot//columns)*stride+gutter+.5)/atlas.height-y*sy
            transform = (sx,0,ox,0,sy,oy)
            if tile_id in spec.get('bottom_trim', []):
                # Rotate UV sampling, leaving the authored atlas untouched.
                sv=(cell-1)/((q.height-1)*atlas.width)
                su=-(cell-1)/((t.pixel_width-1)*atlas.height)
                transform=(0,sv,((slot%columns)*stride+gutter+.5)/atlas.width-y*sv,
                           su,0,((slot//columns)*stride+gutter+cell-.5)/atlas.height-x*factor*su)
            entries.append(struct.pack('<6I2Q6f2I',x,y,q.width_words,q.height,cx,cy,
                pixel_hash,clut_hash,*transform,3,t.mode))
            report.append(dict(player=player+1,tile=tile_id,source_cell=spec['remap'].get(tile_id,tile_id),
                bottom_trim=tile_id in spec.get('bottom_trim', []),
                rect=[x,y,q.width_words,q.height],clut=[cx,cy],depth=t.mode))
    (directory/'mapping.bin').write_bytes(b'HDMAP002'+struct.pack('<I',len(entries))+b''.join(entries))
    (directory/'pack-report.json').write_text(json.dumps(dict(character=spec['character'],model=spec['model'],
        record=spec['record'],source_sha256=spec['sha'],authored_art=source.name,authored_art_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        atlas_size=atlas.size,body_tiles=sorted(body_ids),preserved_tiles=[i for i in range(len(tiles)) if i not in spec['selected']],
        tiles=report),indent=2)+'\n',encoding='utf-8')
    print(f'{directory.name}: {len(entries)} guarded tiles, {atlas.width}x{atlas.height}')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--skin',choices=list(SPECS)+['all'],default='all')
    args=ap.parse_args()
    table,_,_=load_us_table(ROOT/'disc/SLUS_004.02')
    with open_bns_source(ROOT/'disc/Tekken 3 (USA) (Track 1).bin') as disc:
        for key,spec in SPECS.items():
            if args.skin not in ('all',key): continue
            entry=table[spec['record']]
            build(disc.read_at(entry.offset,entry.size),spec,ROOT/'mods/assets'/key)

if __name__=='__main__': main()

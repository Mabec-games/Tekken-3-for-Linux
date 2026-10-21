"""Offline real-disc texture matching checks; no game process or save-state load."""
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from new_character_skin_pack import ROOT, SPECS, costume_tile_ids
from bns_tool import load_us_table, open_bns_source
from tim_tool import scan_tims

def heihachi_mesh_queries(model,tiles,selected,path):
    """Audit all eight previously omitted tiles against native PS1 mesh UVs.

    This format uses absolute row offsets and 16-bit material/UV tables,
    unlike the imported arcade model format.
    """
    assert model[8:12]==b'3DMK'
    word=lambda at:struct.unpack_from('<I',model,at)[0]
    half=lambda at:struct.unpack_from('<H',model,at)[0]
    hits={i:0 for i in range(25,33)}
    queries=[]
    for row in range(word(0)):
        material=word(32+row*56)
        if not material:continue
        uv=material+half(material)
        stream=uv+half(uv)
        for kind in range(4):
            count=model[stream];stream+=1
            for _ in range(count):
                mat=half(material+2+model[stream]*2);stream+=1
                coords=[]
                for _ in range(4 if kind&1 else 3):
                    point=half(uv+2+model[stream]*2);stream+=1
                    coords.append((point&255,point>>8))
                depth=1 if mat&0x8000 else 0
                cx=(mat&63)*16;cy=(mat&0x7fff)>>6
                factor=2 if depth else 4
                for i in hits:
                    t=tiles[i];q=t.image;c=t.clut
                    if (depth,cx,cy)!=(t.mode,c.x,c.y):continue
                    if not all(q.x*factor<=u<(q.x+q.width_words)*factor and q.y<=v<q.y+q.height for u,v in coords):continue
                    hits[i]+=1
                    triangles=[coords[:3]]
                    if len(coords)==4:triangles.append(coords[1:])
                    for player in (0,1):
                        for tri in triangles:
                            queries.append(struct.pack('<12I',384,256*player,depth,cx,504+4*player+cy,
                                *(p[0] for p in tri),*(p[1] for p in tri),int(i in selected)))
    assert hits=={25:8,26:24,27:12,28:9,29:12,30:3,31:12,32:6},hits
    assert all(i in selected for i in range(25,32)) and 32 not in selected
    path.write_bytes(b''.join(queries))
    print('Retail model: 80 previously missed clothing polygons mapped; 6 button-detail polygons preserved')

work=ROOT/'workspace/new-skins-20260920'
work.mkdir(exist_ok=True)
compiler=ROOT.parent/'.tools/toolchain-v1.0.10/bin/clang.exe'
matcher=work/'skin-match-test.exe'
subprocess.run([str(compiler),'-std=c11','-Wall','-Wextra','-I',str(ROOT/'psxrecomp/runtime/include'),
    str(ROOT/'tools/tests/character_skin_match_test.c'),'-o',str(matcher)],check=True)
table,_,_=load_us_table(ROOT/'disc/SLUS_004.02')
keys=list(SPECS)
with open_bns_source(ROOT/'disc/Tekken 3 (USA) (Track 1).bin') as disc:
    for index,(key,spec) in enumerate(SPECS.items()):
        entry=table[spec['record']];raw=disc.read_at(entry.offset,entry.size)
        assert hashlib.sha256(raw).hexdigest()==spec['sha']
        tiles=scan_tims(raw);vram=bytearray(1024*512*2)
        body_ids=costume_tile_ids(raw,tiles)
        assert len(body_ids)=={'eddy-monochrome':28,'julia-blue':31,'heihachi-tiger-coat':33}[key]
        for i in sorted(body_ids):
            t=tiles[i]
            for block,x,y in ((t.image,384+t.image.x,t.image.y),(t.clut,t.clut.x,504+t.clut.y)):
                for row in range(block.height):
                    src=block.data_offset+row*block.width_words*2
                    dst=((y+row)*1024+x)*2
                    vram[dst:dst+block.width_words*2]=raw[src:src+block.width_words*2]
        capture=work/f'{key}-synthetic-vram.bin';capture.write_bytes(vram)
        folder=ROOT/'mods/assets'/key
        report=json.loads((folder/'pack-report.json').read_text())
        mapping=(folder/'mapping.bin').read_bytes()
        assert mapping[:8]==b'HDMAP002'
        assert struct.unpack_from('<I',mapping,8)[0]==len(spec['selected'])*2
        assert len(mapping)==12+72*len(spec['selected'])*2
        assert all(i in report['preserved_tiles'] for i in set(range(len(tiles)))-body_ids)
        if key=='heihachi-tiger-coat':
            # Every red-coat panel and shoe is mapped, including third-row
            # palettes; mixed skin/cuff and every face/skin/hair tile stay stock.
            assert {12,14,15,17,20,18,23,25,26,27,28,29,30,31} <= set(spec['selected'])
            assert {0,1,5,6,7,11,19,21,22,24,32} <= set(report['preserved_tiles'])
            assert report['body_tiles']==list(range(33))
            assert report['authored_art']=='authored-atlas-v2.png'
            assert any(t['tile']==20 and t['clut'][1]==506 for t in report['tiles'])
            assert any(t['tile']==23 and t['clut'][1]==510 for t in report['tiles'])
        for tile in report['tiles']:
            assert tile['tile'] in spec['selected']
        rgba=(folder/f'{spec["name"]}.rgba').read_bytes()
        w,h=struct.unpack_from('<II',rgba,8)
        assert rgba[:8]==b'HDRGBA01' and len(rgba)==16+w*h*4
        # Native UV corners must stay in the packed cell, also for rectangular
        # tiles whose trim is rotated onto the bottom edge.
        for n,tile in enumerate(report['tiles']):
            entry=struct.unpack_from('<6I2Q6f2I',mapping,12+n*72)
            x,y,tw,th=entry[:4];a,b,c,d,e,f=entry[8:14]
            factor=2 if tile['depth'] else 4
            slot=n%len(spec['selected'])
            left=(slot%4)*288+16+.5;top=(slot//4)*288+16+.5
            samples=[((a*u+b*v+c)*w,(d*u+e*v+f)*h)
                     for u in (x*factor,(x+tw)*factor-1) for v in (y,y+th-1)]
            assert abs(min(p[0] for p in samples)-left)<.02
            assert abs(max(p[0] for p in samples)-(left+255))<.02
            assert abs(min(p[1] for p in samples)-top)<.02
            assert abs(max(p[1] for p in samples)-(top+255))<.02
            if tile['tile'] in spec.get('bottom_trim',[]):
                assert a==e==0 and b>0 and d<0
        for other in keys:
            if other==key:continue
            extra=[]
            if key=='heihachi-tiger-coat':
                entry=table[spec['record']-2]
                queries=work/'heihachi-retail-mesh-queries.bin'
                heihachi_mesh_queries(disc.read_at(entry.offset,entry.size),tiles,set(spec['selected']),queries)
                extra=[str(queries)]
            subprocess.run([str(matcher),str(folder/'mapping.bin'),
                str(ROOT/'mods/assets'/other/'mapping.bin'),str(capture),*extra],check=True)
print('PASS: three real-disc costume identities, both VRAM placements, six cross-pack checks, mutations and shared-effect exclusion')

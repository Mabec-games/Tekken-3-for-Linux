"""Offline renderer-map contract check; no game launch or save files."""
from pathlib import Path
import struct
import subprocess
import numpy as np
from tim_tool import scan_tims

ROOT=Path(__file__).resolve().parents[1]
def main():
    assets=ROOT/'mods/assets/jun-heavenly-garden/native'
    arc=(assets/'Heavenly-Garden.arc').read_bytes()
    mesh=(assets/'Heavenly-Garden.mesh').read_bytes()
    vram=np.zeros((512,1024),dtype='<u2')
    for tile in scan_tims(arc):
        for b in (tile.clut,tile.image):
            vram[b.y:b.y+b.height,b.x:b.x+b.width_words]=np.frombuffer(
                arc[b.data_offset:b.end_offset],dtype='<u2').reshape(b.height,b.width_words)
    queries=bytearray()
    for row in range(struct.unpack_from('<I',mesh,8)[0]):
        desc=struct.unpack_from('<7I',mesh,12+row*28)
        for i in range(desc[3]):
            p=12+desc[4]+20*i;q=mesh[p:p+20]
            clut,page=struct.unpack_from('<H',q,6)[0],struct.unpack_from('<H',q,10)[0]
            uv=[(q[4],q[5]),(q[8],q[9]),(q[12],q[13]),(q[14],q[15])]
            depth=(page>>7)&3
            for tri in ((0,1,2),(1,2,3)) if q[3]==0x2c else ((0,1,2),):
                queries+=struct.pack('<12I',(page&15)*64,(page&16)*16,depth,
                    (clut&63)*16,clut>>6,*[uv[k][0] for k in tri],*[uv[k][1] for k in tri],int(depth==1))
    # Water has its own kind/UVs and must NEVER sample the panorama.
    for y in (0,64,128,192):
        queries+=struct.pack('<12I',512,0,0,224,499,192,255,192,y,y,y+63,2)
        # Adjacent UI pixels / other palettes must not become water.
        queries+=struct.pack('<12I',512,0,0,224,498,192,255,192,y,y,y+63,0)
        queries+=struct.pack('<12I',512,0,0,224,499,0,63,0,y,y,y+63,0)
    out=ROOT/'build-release/jun-stage-check';out.mkdir(exist_ok=True)
    (out/'vram.bin').write_bytes(vram.tobytes());(out/'background-queries.bin').write_bytes(queries)
    exe=out/'background-test.exe'
    subprocess.run([str(ROOT.parent/'.tools/toolchain-v1.0.10/bin/clang.exe'),'-std=c11','-O2',
        '-I'+str(ROOT/'psxrecomp/runtime/include'),str(ROOT/'tools/tests/jun_background_match_test.c'),'-o',str(exe)],check=True)
    subprocess.run([str(exe),str(assets/'background-mapping.bin'),str(out/'vram.bin'),str(out/'background-queries.bin')],check=True)
    payload=(assets/'background.rgba').read_bytes()
    assert payload[:8]==b'HDRGBA01'
    w,h=struct.unpack_from('<II',payload,8)
    assert (w,h)==(2172,331) and len(payload)==16+w*h*4
    pixels=np.frombuffer(payload[16:],dtype='uint8').reshape(h,w,4)
    assert len(np.unique(pixels[:,:,:3].reshape(-1,3),axis=0))>256
    # Measure the final TIM floor, not just the authoring PNG.
    from tim_tool import decode_rgba
    floor_tile=scan_tims(arc)[-1]
    floor=np.frombuffer(decode_rgba(arc,floor_tile),dtype='uint8').reshape(-1,4)
    water=pixels[-4:,:,:3].mean(axis=(0,1))
    delta=abs(water-floor[:,:3].mean(axis=0))
    assert delta.max()<12,delta
    ground_payload=(assets/'ground.rgba').read_bytes()
    assert ground_payload[:16]==b'HDRGBA01'+struct.pack('<II',64,64)
    assert ground_payload[16:]==decode_rgba(arc,floor_tile)
    print('Full-colour 2172 x 331 host backdrop; native floor/water colour delta:',delta)

if __name__=='__main__':main()

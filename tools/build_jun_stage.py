"""Build Jun's native PS1 stage textures from authored art and verified local geometry.

No disc is modified. The stock forest supplies only a compatible backdrop mesh,
texture allocation and environment/collision metadata, not artwork. Backdrop
UVs are rebuilt against overlapping, unique panorama pages (the original UVs
repeat half of the forest around the other half of the cylinder).
Every texture and palette in the new arena is authored Heavenly Garden content.
"""
from pathlib import Path
import hashlib
import json
import struct
import numpy as np
from PIL import Image
from forest_hd_pack import TEXTURE_SHA, MODEL_SHA, fnv
from tim_tool import scan_tims, decode_rgba

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'mods/assets/jun-heavenly-garden'


def native_preview(texture_data, model, tiles):
    """Diagnostic unwrapped rasterization of actual mesh + final shared VRAM."""
    vram=np.zeros((512,1024),dtype='<u2')
    for tile in tiles:
        for block in (tile.clut,tile.image):
            vram[block.y:block.y+block.height,block.x:block.x+block.width_words]=np.frombuffer(
                texture_data,dtype='<u2',offset=block.offset+12,
                count=block.height*block.width_words).reshape(block.height,block.width_words)
    w,h=1536,224
    canvas=np.zeros((h,w,3),dtype=np.uint8)
    covered=np.zeros((h,w),dtype=bool)
    for row in range(struct.unpack_from('<I',model,8)[0]):
        desc=struct.unpack_from('<7I',model,12+row*28)
        vertices=np.array([struct.unpack_from('<4h',model,12+desc[0]+i*8)[:3] for i in range(desc[1])])
        for j in range(desc[3]):
            off=12+desc[4]+j*20;q=model[off:off+20];n=4 if q[3]==0x2c else 3
            xyz=vertices[list(q[16:16+n])]
            angles=np.arctan2(xyz[:,0],xyz[:,2])
            if np.ptp(angles)>np.pi:angles=np.where(angles<0,angles+2*np.pi,angles)
            pos=np.stack(((angles+np.pi)/(2*np.pi)*w,(xyz[:,1]+1280)/1280*h),axis=1)
            uv=np.array([(q[4],q[5]),(q[8],q[9]),(q[12],q[13]),(q[14],q[15])],dtype=float)
            clut,page=struct.unpack_from('<H',q,6)[0],struct.unpack_from('<H',q,10)[0]
            for tri in ([(0,1,2),(1,2,3)] if n==4 else [(0,1,2)]):
                p=pos[list(tri)];t=uv[list(tri)]
                left,top=np.floor(p.min(axis=0)).astype(int);right,bottom=np.ceil(p.max(axis=0)).astype(int)
                top=max(0,top);bottom=min(h-1,bottom)
                if bottom<top or right<left:continue
                mat=np.column_stack((p,np.ones(3)))
                if abs(np.linalg.det(mat))<1e-5:continue
                yy,xx=np.mgrid[top:bottom+1,left:right+1]
                bary=np.stack((xx+.5,yy+.5,np.ones_like(xx)),axis=-1)@np.linalg.inv(mat)
                inside=(bary>=-1e-5).all(axis=-1)
                uv_at=np.rint(bary@t).astype(int)
                depth=(page>>7)&3
                assert depth in (0,1)
                per_word=4 if depth==0 else 2
                bits=16//per_word
                tx=(page&15)*64*per_word+uv_at[:,:,0];ty=(page&16)*16+uv_at[:,:,1]
                index=(vram[ty%512,(tx//per_word)%1024]>>((tx%per_word)*bits))&((1<<bits)-1)
                color=vram[clut>>6,(clut&63)*16+index]
                rgb=np.stack((color&31,(color>>5)&31,(color>>10)&31),axis=-1)
                rgb=((rgb*255+15)//31).astype('uint8')
                canvas[yy[inside],xx[inside]%w]=rgb[inside]
                covered[yy[inside],xx[inside]%w]=True
    Image.fromarray(canvas).save(ASSETS/'native-background-preview.png')
    return float(covered.mean())


def indexed(image, colors):
    image=image.convert('RGB').quantize(colors=colors,method=Image.Quantize.MEDIANCUT)
    entries=image.getpalette()[:colors*3]
    entries += [0]*(colors*3-len(entries))
    rgb=np.array(entries,dtype=np.uint16).reshape(colors,3)>>3
    words=rgb[:,0]|(rgb[:,1]<<5)|(rgb[:,2]<<10)
    words[words==0]=1  # opaque near-black, not PS1 transparent zero
    return np.array(image),words.astype('<u2').tobytes()


def tim(pixels,palette,x,y,cx,cy,depth):
    h,w=pixels.shape
    data=pixels.tobytes() if depth==1 else (pixels[:,::2]|(pixels[:,1::2]<<4)).tobytes()
    words=w//(2 if depth==1 else 4)
    return (struct.pack('<II',16,8|depth)+
            struct.pack('<I4H',12+len(palette),cx,cy,len(palette)//2,1)+palette+
            struct.pack('<I4H',12+len(data),x,y,words,h)+data)


def main():
    stock = (ROOT/'workspace/forest-research/records/038.arc').read_bytes()
    model = bytearray((ROOT/'workspace/forest-research/records/058.bin').read_bytes())
    assert hashlib.sha256(stock).hexdigest()==TEXTURE_SHA
    assert hashlib.sha256(model).hexdigest()==MODEL_SHA
    stock_tiles=scan_tims(stock)
    # 768x192, 256 RGB555 colors: genuinely native, deliberately PS1-resolution.
    # Six overlapping 160px pages eliminate UV page-boundary splits. All page
    # allocations fit INSIDE the stock stage's footprint, clear of fighter/UI VRAM.
    panorama,palette=indexed(Image.open(ASSETS/'background.png').convert('RGB').resize((768,192),Image.Resampling.BOX),256)
    pages=[(0,576,0),(128,656,0),(256,736,0),(384,512,256),(512,592,256),(640,672,256)]
    stream=bytearray()
    for start,x,y in pages:
        stream+=tim(panorama[:,(np.arange(160)+start)%768],palette,x,y,0,480,1)
    sky=stock_tiles[473]
    sky_rgb=np.array(Image.open(ASSETS/'background.png').convert('RGB'))[0].mean(axis=0).astype('uint16')>>3
    sky_word=int(sky_rgb[0]|(sky_rgb[1]<<5)|(sky_rgb[2]<<10)) or 1
    stream+=tim(np.zeros((sky.image.height,sky.pixel_width),dtype='uint8'),
                struct.pack('<16H',*([sky_word]*16)),sky.image.x,sky.image.y,0,481,0)
    ground,ground_palette=indexed(Image.open(ASSETS/'ground.png'),16)
    for tile in stock_tiles[-4:]:
        stream+=tim(ground,ground_palette,tile.image.x,tile.image.y,tile.clut.x,tile.clut.y,0)
    stream+=bytes(4)  # native concatenated-TIM terminator
    env_off,env_size=struct.unpack_from('<II',stock,12)
    environment=stock[env_off:env_off+env_size]
    output=bytearray(struct.pack('<6I',2,24,len(stream),24+len(stream),len(environment),0xffffffff))
    output+=stream+environment
    assert len(output)<=len(stock)
    output+=bytes(len(stock)-len(output))  # retain the proven loader buffer budget

    mapped=0
    for row in range(struct.unpack_from('<I',model,8)[0]):
        desc=struct.unpack_from('<7I',model,12+row*28)
        vertices=np.array([struct.unpack_from('<4h',model,12+desc[0]+i*8)[:3] for i in range(desc[1])])
        for j in range(desc[3]):
            off=12+desc[4]+j*20
            assert model[off+3] in (0x24,0x2c)
            model[off:off+3]=bytes((128,128,128))
            n=4 if model[off+3]==0x2c else 3
            xyz=vertices[list(model[off+16:off+16+n])]
            if xyz[:,1].max()<=-1279:  # dome: retain safe tiny UVs, author sky color
                struct.pack_into('<H',model,off+6,481<<6)
                continue
            angles=np.arctan2(xyz[:,0],xyz[:,2])
            if np.ptp(angles)>np.pi:angles=np.where(angles<0,angles+2*np.pi,angles)
            pu=(angles+np.pi)*768/(2*np.pi)
            candidates=[(start+turn*768,x,y) for start,x,y in pages for turn in (-1,0,1)
                        if np.all(pu-(start+turn*768)>=0) and np.all(pu-(start+turn*768)<=159)]
            assert candidates, (row,j,pu)
            start,x,y=candidates[0]
            u=np.rint(pu-start+(x%64)*2).astype(int)
            v=np.rint(np.clip((xyz[:,1]+1280)/1280,0,1)*191).astype(int)
            for k,uv_off in enumerate((4,8,12,14)[:n]):
                model[off+uv_off:off+uv_off+2]=bytes((u[k],v[k]))
            struct.pack_into('<H',model,off+6,480<<6)
            struct.pack_into('<H',model,off+10,(x//64)|((y//256)<<4)|(1<<7))
            mapped+=1

    runtime=ASSETS/'native'
    runtime.mkdir(exist_ok=True)
    assets={'Heavenly-Garden.arc':bytes(output),'Heavenly-Garden.mesh':bytes(model)}
    specs={}
    for name,data in assets.items():
        (runtime/name).write_bytes(data)
        specs[name]={'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    tiles=scan_tims(output)
    assert len(output)==len(stock) and len(tiles)==11 and mapped==640
    # Optional OpenGL presentation: sample the authored panorama directly,
    # guarded by BOTH native pixels and CLUT. Never replace a whole VRAM page
    # blindly: the same memory is reused by other arenas and UI screens.
    records=bytearray()
    for tile,(start,x,y) in zip(tiles[:6],pages):
        b,c=tile.image,tile.clut
        matrix=(1/768,0,(start-x*2)/768,0,1/191,-y/191)
        records+=struct.pack('<6I2Q6fII',b.x,b.y,b.width_words,b.height,c.x,c.y,
            fnv(output[b.data_offset:b.end_offset]),fnv(output[c.data_offset:c.end_offset]),
            *matrix,1,1)
    # Match Jun's four floor tiles independently of the backdrop. The host
    # water shader replaces inherited forest distance-darkening only for
    # these exact pixels + CLUT, not arbitrary ground or shadow primitives.
    for tile in tiles[-4:]:
        b,c=tile.image,tile.clut
        matrix=(1/64,0,-b.x*4/64,0,1/64,-b.y/64)
        records+=struct.pack('<6I2Q6fII',b.x,b.y,b.width_words,b.height,c.x,c.y,
            fnv(output[b.data_offset:b.end_offset]),fnv(output[c.data_offset:c.end_offset]),
            *matrix,2,0)
    (runtime/'background-mapping.bin').write_bytes(b'HDMAP002'+struct.pack('<I',10)+records)
    (runtime/'background.rgba').write_bytes((ASSETS/'background.rgba').read_bytes())
    # Use the decoded native palette, so the shared join colour is the actual
    # water material rather than a hand-entered approximation from the sky.
    floor_tile=tiles[-1]
    (runtime/'ground.rgba').write_bytes(b'HDRGBA01'+struct.pack('<II',64,64)+
                                      decode_rgba(output,floor_tile))
    for name in ('background-mapping.bin','background.rgba','ground.rgba'):
        data=(runtime/name).read_bytes()
        specs[name]={'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    # Prove every upload stays within the original stage's texture/palette VRAM.
    allowed=np.zeros((512,1024),dtype=bool)
    for tile in stock_tiles:
        for b in (tile.clut,tile.image):allowed[b.y:b.y+b.height,b.x:b.x+b.width_words]=True
    for tile in tiles:
        for b in (tile.clut,tile.image):assert allowed[b.y:b.y+b.height,b.x:b.x+b.width_words].all()
    # Verify floor as actually encoded in the native pack, not just the source PNG.
    t=tiles[-1]
    Image.frombytes('RGBA',(t.pixel_width,t.image.height),decode_rgba(output,t)).resize(
        (512,512),Image.Resampling.NEAREST).save(ASSETS/'native-floor-preview.png')
    coverage=native_preview(output,model,tiles)
    manifest={'stage_id':20,'music_id':16,'base_geometry':'verified US forest cylinder',
              'renderer':'native fallback; guarded full-detail backdrop on OpenGL',
              'host_background_size':list(Image.open(ASSETS/'background.png').size),
              'texture_count':len(tiles),'panorama_size':[768,192],'panorama_colors':256,
              'floor_size':[64,64],'floor_colors':16,'remapped_primitives':mapped,
              'diagnostic_panorama_coverage':coverage,'assets':specs}
    (runtime/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__': main()

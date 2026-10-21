"""Offline production stage checks. Never launches the game or touches saves."""
from pathlib import Path
import shutil
import struct
import subprocess
import ctypes
from test_jun_cpu import Machine, ROOT, MODE, half
from unicorn.mips_const import UC_MIPS_REG_A0, UC_MIPS_REG_A1
from tim_tool import scan_tims
from bns_tool import load_us_table, open_bns_source


def main():
    out=ROOT/'build-release/jun-stage-check';out.mkdir(exist_ok=True)
    runtime=out/'runtime'
    pack=runtime/'mods/jun-heavenly-garden';pack.mkdir(parents=True,exist_ok=True)
    for name in ('Heavenly-Garden.arc','Heavenly-Garden.mesh'):
        shutil.copyfile(ROOT/'mods/assets/jun-heavenly-garden/native'/name,pack/name)
    exe=(ROOT/'disc/SLUS_004.02').read_bytes()
    base=struct.unpack_from('<I',exe,24)[0]&0x1fffffff
    ram=bytearray(0x800000);ram[base:base+len(exe)-2048]=exe[2048:]
    before=out/'input.ram';after=out/'patched.ram';before.write_bytes(ram)
    binary=out/'stage-test.exe'
    subprocess.run([str(ROOT.parent/'.tools/toolchain-v1.0.10/bin/clang.exe'),'-std=c11','-O2',
        '-I'+str(ROOT/'tools/tests/jun-stage-stubs'),'-I'+str(ROOT/'psxrecomp/runtime/include'),
        str(ROOT/'tools/tests/jun_stage_test.c'),str(ROOT/'psxrecomp/runtime/src/psx_sha256.c'),
        '-o',str(binary)],check=True)
    subprocess.run([str(binary),str(before),str(runtime)+'/',str(after),'valid'],check=True)
    subprocess.run([str(binary),str(before),str(out/'missing')+'/',str(after),'missing'],check=True)
    corrupt=out/'corrupt/mods/jun-heavenly-garden';corrupt.mkdir(parents=True,exist_ok=True)
    bad=bytearray((pack/'Heavenly-Garden.arc').read_bytes());bad[100]^=1
    (corrupt/'Heavenly-Garden.arc').write_bytes(bad)
    subprocess.run([str(binary),str(before),str(out/'corrupt')+'/',str(after),'missing'],check=True)
    policy_dll=out/'stage-policy.dll'
    subprocess.run([str(ROOT.parent/'.tools/toolchain-v1.0.10/bin/clang.exe'),'-std=c11','-O2','-shared',
        '-I'+str(ROOT/'tools/tests/jun-stage-stubs'),'-I'+str(ROOT/'psxrecomp/runtime/include'),
        str(ROOT/'tools/tests/jun_stage_test.c'),str(ROOT/'psxrecomp/runtime/src/psx_sha256.c'),
        '-o',str(policy_dll)],check=True)
    policy=ctypes.CDLL(str(policy_dll)).jun_prepare_check
    policy.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32),ctypes.c_uint,ctypes.c_uint]
    policy.restype=None
    def prepare(m,loader=False,pc=0):
        state=ctypes.create_string_buffer(m.read(MODE,0xc0),0xc0)
        addresses=(0x800adc84,0x800add08,0x800b053e,0x800a08b0,0x800a08a0)
        values=(ctypes.c_uint32*5)(*[int.from_bytes(m.read(a,1 if i==2 else 2),'little') for i,a in enumerate(addresses)])
        policy(state,m.read(0x800add5c,4),values,pc,int(loader))
        m.write(MODE,state.raw)
        for i,a in enumerate(addresses):
            if i!=2:m.h(a,values[i])
    patched=after.read_bytes()
    # Reproduce the player's captured fight-6 state, with no stage-commit
    # callback at all: Paul (6) vs Jun (23), Eddy stage/music 10/1. Exercise
    # actual host entry wrappers, not a hand-written substitute policy.
    regression=Machine(patched)
    regression.write(MODE,bytes(0xc0));regression.w(MODE,4)
    regression.b(MODE+0x1c,1);regression.b(MODE+0x1f,1)
    regression.h(0x800add5c,6);regression.h(0x800add5e,23)
    regression.h(0x800adc84,10);regression.h(0x800add08,1)
    regression.write(MODE+0x1a,bytes((10,1)))
    regression.h(0x800a08a0,3);regression.h(0x800a08b0,10)
    prepare(regression)
    assert regression.read(MODE+0x1a,2)==bytes((20,16))
    assert regression.read(0x800adc84,2)==bytes((20,0))
    prepare(regression,loader=True)
    assert regression.call(0x8006c63c,16,0)==1
    regression.call(0x8006c63c,16,1)
    prepare(regression,loader=True)
    assert regression.call(0x8006c63c,16,0)==0 # same arena already loaded
    # Different CPU fighters, mode-owned arenas, invalid sides and resumed
    # CPS entries must not be changed. Also cover both human/controller sides.
    cases=0
    for mode in range(9):
        for players in (0,1,2):
            for side in (0,1,2):
                for owner in (0,1,2):
                    for chars in ((6,23),(23,6),(6,1)):
                        for loader in (False,True):
                            regression.write(MODE,bytes([0xa5])*0xc0)
                            regression.w(MODE,mode);regression.b(MODE+0x1c,players)
                            regression.b(MODE+0x1f,side);regression.b(0x800b053e,owner)
                            regression.h(0x800add5c,chars[0]);regression.h(0x800add5e,chars[1])
                            regression.h(0x800adc84,10);regression.h(0x800add08,1)
                            regression.h(0x800a08a0,3);regression.h(0x800a08b0,10)
                            before_state=regression.read(MODE,0xc0)
                            chosen=side if players==1 else owner if players==2 and mode in (1,2,5) else 2
                            applies=mode<=5 and chosen<2 and chars[chosen]==23
                            prepare(regression,loader,0x80036600 if loader else 0x800524ec)
                            expected=bytearray(before_state)
                            if applies:expected[0x1a:0x1c]=bytes((20,16))
                            assert regression.read(MODE,0xc0)==expected
                            assert regression.read(0x800adc84,2)==half(20 if applies else 10)
                            assert regression.read(0x800add08,2)==half(16 if applies else 1)
                            assert regression.read(0x800a08a0,2)==half(3)
                            assert regression.read(0x800a08b0,2)==half(20 if applies and loader else 10)
                            cases+=1
    for loader,pc in ((False,0x80052510),(True,0x800368b4),(True,0x80036924)):
        regression.w(MODE,4);regression.b(MODE+0x1c,1);regression.b(MODE+0x1f,1)
        regression.h(0x800add5e,23);regression.h(0x800adc84,10)
        prepare(regression,loader,pc)
        assert regression.read(0x800adc84,2)==half(10)
    print(f'Captured Survival fallback corrected before loading; {cases} boundary/ownership cases and CPS continuation guards passed')
    # Run the original ARC accessor and TIM reader; only the GPU/DMA boundary
    # is stubbed. This verifies native 8bpp support and every upload rectangle.
    native=Machine(patched);arc=(pack/'Heavenly-Garden.arc').read_bytes()
    native.write(0x80100000,arc)
    assert native.call(0x80031cbc,0,0x80100000)==0x80100018
    env_offset=struct.unpack_from('<I',arc,12)[0]
    assert native.call(0x80031cbc,1,0x80100000)==0x80100000+env_offset
    uploads=[]
    def upload():
        rect=native.u.reg_read(UC_MIPS_REG_A0);data=native.u.reg_read(UC_MIPS_REG_A1)
        x,y,w,h=struct.unpack('<4H',native.read(rect,8))
        uploads.append((x,y,w,h,native.read(data,w*h*2)))
        return 0
    native.stub(0x8007c650,upload);native.stub(0x8007c3a4,lambda:0)
    assert native.call(0x8006e37c,0x80100018)==11
    expected=[]
    for tile in scan_tims(arc):
        for b in (tile.clut,tile.image):
            expected.append((b.x,b.y,b.width_words,b.height,arc[b.data_offset:b.end_offset]))
    assert uploads==expected
    # Distinct stage IDs must dirty and refresh the stock stage cache in both
    # directions, including two successive rounds on Heavenly Garden.
    native.h(0x800a08a0,8)
    prior=8
    for stage in (20,20,4,20,8,4,8,20):
        native.call(0x8006c618,stage,0,0,0)
        assert native.call(0x8006c63c,16,0)==int(stage!=prior)
        native.call(0x8006c63c,16,1)
        assert native.call(0x8006c63c,16,0)==0
        prior=stage
    print('Native TIM uploads and Jun/Forest/Jin stage-cache transitions passed')
    # Execute native table consumers with the actual production RAM patches.
    for stage in range(21):
        ref=Machine(ram);mod=Machine(patched)
        reference=4 if stage==20 else stage
        for routine in (0x80039e74,0x80039e9c,0x80039ec4):
            expected=0x00808080 if stage==20 and routine==0x80039e74 else ref.call(routine,reference)
            assert mod.call(routine,stage)==expected,(hex(routine),stage)
        ref.call(0x80039e44,reference,0x801e0000,0x801e0004)
        mod.call(0x80039e44,stage,0x801e0000,0x801e0004)
        assert mod.read(0x801e0000,8)==ref.read(0x801e0000,8)
    # Exercise the real mode-dependent home-stage chooser with Jun's private
    # descriptor. Other stages and Force/Ball overrides remain native.
    m=Machine(patched)
    assert m.value(0x8004f728)==0xa444dc84
    table=0x80430000;desc=table+0x200
    m.write(table,bytes(ram[0x97d40:0x97d40+92*4]));m.write(desc,bytes(ram[0x22274:0x22280]))
    m.b(desc+10,20);m.b(desc+11,16)
    for outfit in range(4):m.w(table+(92+outfit)*4,desc)
    for addr in (0x8004f478,0x8004f580,0x8004f5e4,0x8004f648,0x8004f70c):
        w=m.value(addr);reg=(w>>16)&31
        m.w(addr,0x3c000000|(reg<<16)|(table>>16))
    for addr in (0x8004f468,0x8004f570,0x8004f5d4,0x8004f638,0x8004f6fc):
        m.w(addr,(m.value(addr)&0xffff0000)|96)
    for addr in (0x8004f4a8,0x8004f4e0):m.w(addr,(m.value(addr)&0xffff0000)|24)
    results=[]
    for mode in (0,1,2,3,4,5,7,8):
        m.write(MODE,bytes(0xc0));m.w(MODE,mode);m.b(MODE+0x1c,1);m.b(MODE+0x1f,1)
        m.b(0x800b053e,1);m.w(0x800b6bf4,1);m.w(MODE+0x44,0xffffffff)
        m.h(0x800add5c,9);m.h(0x800add5e,23)
        m.h(0x800add98,0);m.h(0x800add9a,0)
        m.call(0x8004f3b0,MODE)
        prepare(m)
        stage=int.from_bytes(m.read(0x800adc84,2),'little')
        music=int.from_bytes(m.read(0x800add08,2),'little')
        assert stage==(19 if mode==7 else 15 if mode==8 else 20),(mode,stage)
        assert music==16,(mode,music)
        results.append((mode,stage,music))
    print('Native table getters: 0..19 preserved, stage 20 valid; home-stage routes:',results)
    # Run the full native Arcade route-entry -> CPU assignment -> stage commit,
    # not just a manually populated character array. Both controller sides,
    # all Jun outfits, initial/rematch state and every ladder index are covered.
    bns,*_=load_us_table(ROOT/'disc/SLUS_004.02')
    with open_bns_source(ROOT/'disc/Tekken 3 (USA) (Track 1).bin') as source:
        overlay=source.read_at(bns[5].offset,bns[5].size)
    m.write(0x800b0548,overlay)
    cases=0
    for side in (0,1):
        for outfit in range(4):
            for ladder in range(10):
                for prior_stage in (0,4,8,14,20):
                    m.write(MODE,bytes(0xc0));m.w(MODE,0);m.w(MODE+0x24,ladder)
                    m.b(MODE+0x1c,1);m.b(MODE+0x1e,1-side);m.b(MODE+0x1f,side)
                    m.write(MODE+0x90+ladder*4,bytes((23,outfit,ladder,0)))
                    m.h(0x800adc84,prior_stage);m.b(MODE+0x1a,prior_stage)
                    m.h(0x800add5c+(1-side)*2,9)
                    m.h(0x800add5c+side*2,0)
                    m.call(0x800b08f8,MODE)
                    assert int.from_bytes(m.read(0x800add5c+side*2,2),'little')==23
                    m.call(0x8004f3b0,MODE)
                    prepare(m)
                    assert m.read(0x800adc84,2)==bytes((20,0))
                    assert m.read(0x800add08,2)==bytes((16,0))
                    assert m.read(MODE+0x1a,2)==bytes((20,16))
                    cases+=1
    # An old/stale descriptor must not choose another arena for an Arcade CPU
    # Jun. Conversely human Jun must not force her arena on another opponent.
    for side in (0,1):
        for other in range(21):
            m.write(MODE,bytes(0xc0));m.w(MODE,0);m.b(MODE+0x1c,1);m.b(MODE+0x1f,side)
            m.h(0x800add5c+side*2,23);m.h(0x800add98+side*2,1)
            m.b(desc+10,other);m.b(desc+11,0)
            m.call(0x8004f3b0,MODE)
            prepare(m)
            assert m.read(MODE+0x1a,2)==bytes((20,16))
            # Swap Jun to the human side and preserve the stock opponent home.
            m.h(0x800add5c+side*2,other);m.h(0x800add98+side*2,0)
            m.h(0x800add5c+(1-side)*2,23)
            stock_desc=int.from_bytes(m.read(table+other*16,4),'little')
            expected=m.read(stock_desc+10,2)
            m.call(0x8004f3b0,MODE)
            prepare(m)
            assert m.read(MODE+0x1a,2)==expected,(side,other,expected)
    m.b(desc+10,20);m.b(desc+11,16)
    print(f'Arcade: {cases} native route/setup/commit cases passed; stale home metadata overridden only for CPU Jun')
    print('Jun stage offline checks passed; live camera/loading presentation awaits player testing.')


if __name__=='__main__':main()

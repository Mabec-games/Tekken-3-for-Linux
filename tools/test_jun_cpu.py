"""Offline execution of original PS1 opponent/AI routines plus production patches.

Requires the local USA disc and `pip install unicorn`. Does not run the game,
load a save state, or change disc/save files. Artifacts go under build-release.
"""
from pathlib import Path
import random
import struct
import subprocess
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import *
from bns_tool import load_us_table, open_bns_source

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build-release'/'jun-cpu-check'
PROFILES=0x9f055000
MODE=0x800afa88
STOP=0x801ff000
def word(v):return struct.pack('<I',v&0xffffffff)
def half(v):return struct.pack('<H',v&65535)

class Machine:
    def __init__(self,ram,seed=0):
        self.u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
        self.u.mem_map(0,0x800000);self.u.mem_write(0,bytes(ram))
        # The allocator returns 0x9F... data addresses, NOT 0x804... RAM.
        # Keep Expansion 1 separate so a truncated MIPS J target cannot pass.
        self.u.mem_map(0x1f000000,0x400000)
        self.u.mem_write(0x1f000000,bytes(ram[0x400000:0x800000]))
        self.rng=random.Random(seed)
        self.stub(0x8004ce54,lambda:self.rng.randrange(65536))
        # Native usage getter's host wrapper maps Jun to saved row 21.
        self.stub(0x80051660,lambda:0)
    def read(self,a,n):return bytes(self.u.mem_read(a&0x1fffffff,n))
    def write(self,a,data):self.u.mem_write(a&0x1fffffff,data)
    def w(self,a,v):self.write(a,word(v))
    def h(self,a,v):self.write(a,half(v))
    def b(self,a,v):self.write(a,bytes([v]))
    def value(self,a):return int.from_bytes(self.read(a,4),'little')
    def stub(self,addr,fn):
        def hook(u,a,n,data):
            result=fn()
            if result is not None:u.reg_write(UC_MIPS_REG_V0,result)
            u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
        self.u.hook_add(UC_HOOK_CODE,hook,begin=addr,end=addr)
    def call(self,pc,*args,end=STOP):
        for reg,val in zip((UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3),args):self.u.reg_write(reg,val)
        self.u.reg_write(UC_MIPS_REG_SP,0x801fe000)
        self.u.reg_write(UC_MIPS_REG_RA,STOP)
        self.u.emu_start(pc,end,count=200000)
        assert self.u.reg_read(UC_MIPS_REG_PC)==end,hex(self.u.reg_read(UC_MIPS_REG_PC))
        return self.u.reg_read(UC_MIPS_REG_V0)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    exe=(ROOT/'disc/SLUS_004.02').read_bytes()
    base=int.from_bytes(exe[24:28],'little')&0x1fffffff
    original=bytearray(0x800000);original[base:base+len(exe)-2048]=exe[2048:]
    table,*_=load_us_table(ROOT/'disc/SLUS_004.02')
    compiler=ROOT.parent/'.tools/toolchain-v1.0.10/bin/clang.exe'
    combat=(ROOT/'src/tekken3_jun_combat.c').read_text()
    wrapper='void __wrap_func_80059890(CPUState *cpu) {'+combat.split('void __wrap_func_80059890(CPUState *cpu) {',1)[1].split('void tekken3_jun_combat_tick',1)[0]
    (OUT/'jun_cpu_command_wrapper.inc').write_text(wrapper)
    command_test=OUT/'command-test.exe'
    subprocess.run([str(compiler),'-std=c11','-O2','-I',str(OUT),str(ROOT/'tools/tests/jun_cpu_command_test.c'),'-o',str(command_test)],check=True)
    subprocess.run([str(command_test)],check=True)
    harness=OUT/'patch-test.exe'
    subprocess.run([str(compiler),'-std=c11','-O2',str(ROOT/'tools/tests/jun_cpu_patch_test.c'),'-o',str(harness)],check=True)
    patched={};raw={}
    with open_bns_source(ROOT/'disc/Tekken 3 (USA) (Track 1).bin') as source:
        for record in (0,5,7):
            data=source.read_at(table[record].offset,table[record].size)
            memory=original.copy();memory[0xb0548:0xb0548+len(data)]=data
            raw[record]=memory
            before=OUT/f'input-{record}.ram';after=OUT/f'patched-{record}.ram'
            before.write_bytes(memory)
            subprocess.run([str(harness),str(before),str(after)],check=True)
            patched[record]=after.read_bytes()
    # Guard the entire Force overlay from accidental edits at reused addresses.
    assert patched[7][0xb0548:0xb0548+table[7].size]==raw[7][0xb0548:0xb0548+table[7].size]
    assert original[0x22274+10:0x22274+12]==bytes([8,16])
    # New-run counters: execute the actual menu clear loops with dirty state.
    for start,end,offset in ((0x800ca490,0x800ca4e0,0x74),(0x800ca544,0x800ca5b4,0x60)):
        m=Machine(patched[0]);m.write(MODE,bytes([0xa5])*0xc0)
        m.u.reg_write(UC_MIPS_REG_S1,MODE)
        m.call(start,end=end)
        assert m.read(MODE+offset,48)==bytes(48)
        assert m.read(MODE+offset+48,4)==bytes([0xa5])*4
    # Arcade/Time Attack preserve final bosses, exclusions, valid outfits.
    for mode in (0,3):
        seen=0
        m=Machine(patched[5],mode)
        for seed in range(256):
            player=([*range(21),23][seed%22])*4+(seed%4)
            m.w(MODE,mode);m.w(0x80097ef0,0x009fffff)
            m.call(0x800b1fcc,0x801e0000,player)
            route=m.read(0x801e0000,40)
            chars=tuple(route[::4])
            assert len(set(chars[:8]))==8 and player//4 not in chars[:8],chars
            assert chars[8:]==((9 if player//4==13 else 13),14),chars
            assert all(c in range(21) or c==23 for c in chars),chars
            assert all(o<=1 for o in route[1::4]),route
            assert tuple(route[2::4])==tuple(range(10)),route
            seen+=23 in chars
        assert seen>0
        print(f'mode {mode}: Jun selected in {seen}/256 routes; bosses/identity/exclusions intact')
    # Survival includes Jun from the first fight, respecting all four recent IDs.
    for stage in range(64):
        # Compare the exact candidate mask before RNG/recent-opponent filtering.
        # Clear s0 still executes; all other native candidates must be unchanged.
        baseline=Machine(raw[5]);m=Machine(patched[5])
        for machine in (baseline,m):
            machine.w(MODE+0x24,stage)
            machine.w(0x800b2720,0x03e00008) # return after building pool
            machine.w(0x800b2724,0)
            machine.call(0x800b26d0,MODE)
        assert m.u.reg_read(UC_MIPS_REG_T0)==baseline.u.reg_read(UC_MIPS_REG_T0)|(1<<23)
        assert m.u.reg_read(UC_MIPS_REG_S0)==0
    for stage in (0,6,7,16,17,50):
        m=Machine(patched[5],stage);seen=set()
        for trial in range(128):
            m.write(MODE,bytes(0xc0));m.w(MODE,4);m.w(MODE+0x24,stage)
            for i in range(4):m.w(MODE+0x50+i*4,22)
            m.call(0x800b26d0,MODE);seen.add(m.value(MODE+0x48)//4)
        assert 23 in seen and not seen&{21,22},(stage,seen)
        for i in range(4):m.w(MODE+0x50+i*4,(23,0,1,2)[i])
        m.call(0x800b26d0,MODE)
        assert m.value(MODE+0x48)//4 not in (23,0,1,2)
    print('Survival: Jun eligible at all progression tiers; recent-opponent exclusions intact')
    m=Machine(patched[5]);m.write(MODE,bytes(0xc0));m.h(MODE+0x60+23*2,2)
    m.u.reg_write(UC_MIPS_REG_S1,MODE);m.u.reg_write(UC_MIPS_REG_S2,23)
    m.call(0x800b1690,end=0x800b16d4)
    assert int.from_bytes(m.read(MODE+0x60+23*2,2),'little')==3
    assert m.u.reg_read(UC_MIPS_REG_A2)==3
    # Team generator fills CPU teams through the original weighted selection.
    m=Machine(patched[5],123);seen=set()
    for trial in range(128):
        m.write(MODE,bytes(0xc0));m.w(MODE,2);m.w(0x80097ef0,0x009fffff)
        team=MODE+0x59;other=MODE+0x66
        m.b(team+12,4);m.b(other+12,4)
        m.call(0x800b225c,0,team,other)
        count=m.read(team+12,1)[0];chars=[x//4 for x in m.read(team,count)]
        assert count==4 and len(set(chars))==4 and not set(chars)&{21,22},chars
        seen.update(chars)
    assert 23 in seen
    for human in (0,1):
        for size in (1,4,8):
            for trial in range(16):
                m.write(MODE,bytes(0xc0));m.w(MODE,2);m.w(0x80097ef0,0x009fffff)
                m.b(team,92);m.b(team+10,1);m.b(team+12,size);m.b(other+12,size)
                m.call(0x800b225c,human,team,other)
                chars=[x//4 for x in m.read(team,size)]
                assert chars[0]==23 and len(set(chars))==size and not set(chars)&{21,22}
    print('Team Battle: valid distinct CPU teams include Jun')
    # All native difficulty/progression combinations, both actor orientations.
    signatures=set()
    for difficulty in range(3):
        for level in range(10):
            baseline=Machine(raw[5]);baseline.w(0x800afa5c,0x800a9228);baseline.w(0x800a867c,0x800aaab4)
            baseline.h(0x800a9240,9);baseline.h(0x800aaacc,9)
            baseline.h(0x800ae208,difficulty);baseline.b(0x800ae211,level)
            baseline.call(0x80061488,0x8009f318,0,0,0)
            native_state=baseline.read(0x8009f318,0x330)
            for own,opponent in ((23,9),(9,23),(23,23)):
                m=Machine(patched[5]);m.w(0x800afa5c,0x800a9228);m.w(0x800a867c,0x800aaab4)
                m.h(0x800a9240,own);m.h(0x800aaacc,opponent)
                m.h(0x800ae208,difficulty);m.b(0x800ae211,level)
                m.call(0x80061488,0x8009f318,0,0,0)
                state=m.read(0x8009f318,0x330)
                assert state==native_state,(difficulty,level,own,opponent)
                assert state[0x314:0x320]==original[0x98260+9*12:0x98260+10*12]
                assert state[0x320:0x32c]==state[0x314:0x320]
                signatures.add(state[0x238:0x2a6])
    assert len(signatures)>1
    print(f'90 CPU profile initializations passed; {len(signatures)} distinct native difficulty/progression profiles retained')
    # Feed every real imported pattern through native command synthesis.
    # The host lookup itself is compiled/tested above; only that lookup is
    # replaced here so the unmodified PS1 consumer runs against the asset.
    pack=(ROOT/'workspace/jun-import/jun/Jun-TTT1-combat.jmv').read_bytes()
    record_count=struct.unpack_from('<I',pack,12)[0];records=struct.unpack_from('<I',pack,28)[0]
    commands=set()
    for i in range(record_count):
        cancel=struct.unpack_from('<I',pack,records+i*56+12)[0]
        for j in range(1024):
            cmd=struct.unpack_from('<H',pack,cancel+j*12)[0]
            if cmd==0xc000:break
            commands.add(cmd)
        else:raise AssertionError('Unterminated cancel list')
    m=Machine(patched[5])
    for cmd in commands:
        result=m.call(0x800618c0,0x8009f318,cmd,0x80450000)
        if cmd&0xc000:
            assert result==0xffffffff,hex(cmd)
        else:
            direction_mask=(cmd>>5)&0x1ff
            index=next((i for i in range(9,0,-1) if int.from_bytes(m.read(0x8002303c+i*2,2),'little')&direction_mask),0)
            expected=int.from_bytes(m.read(0x80023050+index*2,2),'little')
            for i in range(4):
                if cmd&(1<<i):expected|=int.from_bytes(m.read(0x80023064+i*2,2),'little')
            assert result==expected,(hex(cmd),result,expected)
    print(f'All {len(commands)} actual Jun command IDs resolve in native CPU input synthesis')
    ro,rn=struct.unpack_from('<II',pack,20);cursor=ro+rn*4
    pattern_count=struct.unpack_from('<I',pack,cursor)[0];cursor+=4
    m=Machine(patched[5]);lookup={};sequences={};pointer=0x80440000
    for i in range(pattern_count):
        cmd,n=struct.unpack_from('<HH',pack,cursor);cursor+=4
        seq=pack[cursor:cursor+n*2];cursor+=n*2
        assert cmd==0xe000+i and 3<=n<=65 and seq[-2:]==bytes(2)
        m.write(pointer,seq);lookup[cmd]=pointer;sequences[cmd]=struct.unpack('<'+'H'*n,seq);pointer+=n*2
    # Keep non-vacuous extended-format coverage even for a pack with no E000s.
    for i,seq in enumerate(((12,0x106,0),(20,6,5,0x206,0),(30,2,3,0x409,0))):
        cmd=0xe400+i;m.write(pointer,struct.pack('<'+'H'*len(seq),*seq));lookup[cmd]=pointer;sequences[cmd]=seq;pointer+=len(seq)*2
    m.stub(0x8002cd7c,lambda:lookup.get(m.u.reg_read(UC_MIPS_REG_A0),0))
    for cmd,seq in sequences.items():
        state=0x8009f318;m.write(state,bytes(0x330))
        assert m.call(0x800618c0,state,cmd,0x80450000)==0xffffffff
        direction=int.from_bytes(m.read(0x8002301c+(seq[1]&15)*2,2),'little')
        buttons=sum(bit for src,bit in ((0x100,0x80),(0x200,0x10),(0x400,0x40),(0x800,0x20)) if seq[1]&src)
        assert int.from_bytes(m.read(state+4,2),'little')==direction|buttons
        assert m.value(state+8)==(lookup[cmd]+4 if seq[2] else 0)
        assert m.value(state+0x5c)==0x80450000
    print(f'Extended input format: {pattern_count} asset sequences + 3 synthetic sequences accepted by native CPU synthesis')
    print('Jun CPU offline checks passed; live gameplay remains a separate player test')

if __name__=='__main__':main()

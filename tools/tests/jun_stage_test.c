/* Exercise the actual production stage initializer, patches and loader. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char ram[8*1024*1024],original[8*1024*1024];
static unsigned code_writes;
static const char *asset_base;
const char *SDL_GetBasePath(void) {return asset_base;}
static unsigned at(uint32_t a) {
    a&=0x1fffffff;
    if(a>=0x1f000000 && a<0x1f400000)a=0x400000+a-0x1f000000;
    assert(a<sizeof ram);return a;
}
uint8_t psx_mod_read_byte(uint32_t a) {return ram[at(a)];}
uint16_t psx_mod_read_half(uint32_t a) {uint16_t v;memcpy(&v,ram+at(a),2);return v;}
uint32_t psx_mod_read_word(uint32_t a) {uint32_t v;memcpy(&v,ram+at(a),4);return v;}
void psx_mod_write_byte(uint32_t a,uint8_t v) {ram[at(a)]=v;}
void psx_mod_write_half(uint32_t a,uint16_t v) {memcpy(ram+at(a),&v,2);}
void psx_mod_write_word(uint32_t a,uint32_t v) {memcpy(ram+at(a),&v,4);}
void psx_mod_write_code_word(uint32_t a,uint32_t v) {psx_mod_write_word(a,v);code_writes++;}
uint32_t psx_mod_alloc_guest_memory(uint32_t size,uint32_t alignment) {
    assert(size==0x400 && alignment==16);return 0x9f028000;
}
#include "../../src/tekken3_jun_stage.c"
static unsigned loading_calls,arena_calls;
void __real_func_800524EC(CPUState *cpu) {(void)cpu;loading_calls++;}
void __real_func_80036600(CPUState *cpu) {(void)cpu;arena_calls++;}
#include "../../src/tekken3_jun_stage_hooks.c"
/* Execute the actual host wrappers with recorded native selection state.
 * Both native calls are stubbed only AFTER the preparation boundary. */
__declspec(dllexport) void jun_prepare_check(uint8_t *mode,
        const uint8_t *characters,uint32_t *values,unsigned pc,unsigned loader) {
    CPUState cpu={0};cpu.pc=pc;cpu.gpr[4]=0x8015c6d8;cpu.gpr[31]=0x80012340;
    CPUState before=cpu;
    memcpy(ram+0xafa88,mode,0xc0);memcpy(ram+0xadd5c,characters,4);
    psx_mod_write_half(0x800adc84,values[0]);psx_mod_write_half(0x800add08,values[1]);
    psx_mod_write_byte(0x800b053e,values[2]);psx_mod_write_half(0x800a08b0,values[3]);
    psx_mod_write_half(0x800a08a0,values[4]);
    ready=1;unsigned calls=loading_calls+arena_calls;
    if(loader)__wrap_func_80036600(&cpu);else __wrap_func_800524EC(&cpu);
    assert(loading_calls+arena_calls==calls+1);
    assert(!memcmp(&cpu,&before,sizeof cpu)); /* continuations/args untouched */
    memcpy(mode,ram+0xafa88,0xc0);
    values[0]=psx_mod_read_half(0x800adc84);values[1]=psx_mod_read_half(0x800add08);
    values[3]=psx_mod_read_half(0x800a08b0);values[4]=psx_mod_read_half(0x800a08a0);
}
int main(int argc,char **argv) {
    assert(argc==5);asset_base=argv[2];
    FILE *f=fopen(argv[1],"rb");assert(f);
    assert(fread(ram,1,sizeof ram,f)==sizeof ram);fclose(f);
    memcpy(original,ram,sizeof ram);
    if(!strcmp(argv[4],"missing")) {
        assert(tekken3_jun_stage_initialize()==8 && !ready && !code_writes);
        assert(!memcmp(ram,original,sizeof ram));
        puts("Missing/invalid stage pack safely retains Jin arena");return 0;
    }
    assert(tekken3_jun_stage_initialize()==20 && ready);
    assert(!memcmp(ram+at(profiles),original+0x96c5c,21*28));
    assert(!memcmp(ram+0x96c5c,original+0x96c5c,22*28));
    assert(!memcmp(ram+0x25138,original+0x25138,21*4));
    assert(psx_mod_read_word(heights+20*4)==psx_mod_read_word(0x80025138+4*4));
    unsigned writes=code_writes;tekken3_jun_stage_tick();
    assert(writes==16 && code_writes==writes);
    assert(psx_mod_read_word(0x8004f728)==0xa444dc84);
    f=fopen(argv[3],"wb");assert(f);assert(fwrite(ram,1,sizeof ram,f)==sizeof ram);fclose(f);
    CPUState c={0};c.pc=0x80052ad0;c.gpr[4]=0x80100000;
    for(unsigned mode=0;mode<=8;mode++) {
        psx_mod_write_word(0x800afa88,mode);
        for(unsigned stage=0;stage<=20;stage++) {
            psx_mod_write_half(0x800adc84,stage);
            for(unsigned pass=0;pass<4;pass++) {
                c.pc=0x80052ad0;c.gpr[5]=(pass&1)?74:54;
                const uint32_t sites[]={0x800368b4,0x80036924,0x800369f0,0x80036a60};
                c.gpr[31]=sites[pass];
                unsigned size=(pass&1)?MESH_SIZE:TEXTURE_SIZE;
                unsigned char *data=(pass&1)?mesh:textures;
                ram[0xfffff]=0xa5;ram[0x100000+size]=0xa5;
                int expected=stage==20 && mode!=7 && mode!=8;
                assert(tekken3_jun_stage_load(&c)==expected);
                if(expected) {
                    assert(!memcmp(ram+0x100000,data,size));
                    assert(c.pc==sites[pass] && c.gpr[2]==0);
                    assert(ram[0xfffff]==0xa5 && ram[0x100000+size]==0xa5);
                }
            }
        }
    }
    psx_mod_write_word(0x800afa88,0);psx_mod_write_half(0x800adc84,20);
    c.pc=0x80052ad0;c.gpr[5]=54;c.gpr[31]=0x80052770;
    assert(!tekken3_jun_stage_load(&c)); /* portrait request cannot be hijacked */
    c.gpr[31]=0x800368b4;c.pc=0x80052b04;
    assert(!tekken3_jun_stage_load(&c)); /* CPS continuation cannot restart load */
    puts("Stage 20: native pack loads, all stock stages, mode isolation, return sites, bounds and idempotence passed");
    return 0;
}

/* Behavioral tests for actor routing and the host mixer, using the real code.
 * Synthetic waveforms keep this test independent of copyrighted source data. */
#include <assert.h>
#include <stdio.h>
#include "../../src/tekken3_jun_voices.c"
static unsigned mode[2]={2,0}, native_calls, game_mode=8;
static int16_t native_pcm=100, main_gain=32767;
static unsigned ctrl=0xc000;
const char *tekken3_jun_asset_root(void) { return NULL; }
unsigned tekken3_jun_player_motion_mode(unsigned p) { return mode[p]; }
uint16_t psx_mod_read_half(uint32_t a) { (void)a;return game_mode; }
void psx_mod_write_word(uint32_t a,uint32_t v) { (void)a;(void)v; }
uint32_t psx_mod_alloc_guest_memory(uint32_t s,uint32_t a) { (void)s;(void)a;return 0; }
void __real_func_80040C90(CPUState *cpu) { native_calls++;cpu->pc=cpu->gpr[31]; }
void __real_spu_render(int16_t *out,int n) { if(out)for(int i=0;i<n*2;i++)out[i]=native_pcm; }
void __real_spu_set_host_mix_volume(int a,int b) { (void)a;(void)b; }
void __real_spu_init(void) {}
int __real_spu_snapshot_read(const uint8_t *p,uint32_t n) { (void)p;return n==1; }
void spu_get_global_state(SpuGlobalState *s) { memset(s,0,sizeof *s);s->ctrl=ctrl; }
uint32_t spu_read(uint32_t a) { (void)a;return (uint16_t)main_gain; }
void psx_sha256_compute(const uint8_t *p,size_t n,uint8_t out[32]) { (void)p;(void)n;memset(out,0,32); }
static void cry(unsigned player,unsigned command) {
    CPUState cpu={0};cpu.gpr[4]=player;cpu.gpr[6]=command;cpu.gpr[31]=0x80012340;
    __wrap_func_80040C90(&cpu);assert(cpu.pc==cpu.gpr[31]);
}
int main(void) {
    static unsigned char pcm[2000];
    for(unsigned i=0;i<1000;i++){pcm[i*2]=0x00;pcm[i*2+1]=0x40;}
    for(unsigned i=0;i<12;i++){samples[i].pcm=pcm;samples[i].frames=1000;}
    loaded=attempted=1;
    int16_t out[1200];
    cry(1,0x2003);assert(native_calls==1 && !voices[1].group);
    for(unsigned i=0;i<7;i++){cry(0,0x2000+i);assert(voices[0].id==164+i);}
    cry(0,0x2007);assert(voices[0].id==164);
    cry(0,0x3004);assert(voices[0].id==161);
    cry(0,0x4002);assert(voices[0].id==163);
    cry(0,0x5003);assert(voices[0].id==171);
    assert(native_calls==1);
    __wrap_spu_render(out,500);assert(out[900]>4000 && out[900]<4300);
    assert(voices[0].pos==500);
    __wrap_spu_set_host_mix_volume(0,100);
    __wrap_spu_render(out,100);for(int i=0;i<200;i++)assert(out[i]==100);
    assert(voices[0].pos==600); /* mute advances time, avoiding delayed cries */
    __wrap_spu_set_host_mix_volume(100,0);main_gain=0;
    __wrap_spu_render(out,100);assert(out[150]==100);
    main_gain=32767;ctrl=0x8000;
    __wrap_spu_render(out,100);assert(out[150]==100);
    ctrl=0xc000;mode[1]=2;
    cry(0,0x2000);cry(1,0x3000);
    __wrap_spu_render(out,500);assert(out[900]>8000);
    assert(voices[0].id==164 && voices[1].id==160);
    native_pcm=30000;cry(0,0x2000);cry(1,0x2000);
    __wrap_spu_render(out,500);assert(out[900]==32767);
    assert(!__wrap_spu_snapshot_read(NULL,0) && voices[0].group);
    assert(__wrap_spu_snapshot_read(NULL,1) && !voices[0].group && !voices[1].group);
    cry(0,0x2000);mode[0]=0;__wrap_spu_render(out,10);assert(!voices[0].group);
    mode[0]=2;cry(0,0x2000);game_mode=9;tekken3_jun_voices_tick();assert(!voices[0].group);
    game_mode=8;cry(0,0x2000);__wrap_spu_init();assert(!voices[0].group);
    puts("Jun voice routing, independent players, gain, mute, saturation and reset: PASS");
    return 0;
}

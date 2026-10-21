#include <assert.h>
#include <stdint.h>
#include <stdio.h>
typedef struct {uint32_t gpr[32],pc;} CPUState;
static int loaded=1,real_calls;
static unsigned pattern_count=3;
static uint32_t patterns[]={0x80400100,0x80400200,0x80400300};
static struct {uint32_t native_base,alias_table;} players[2]={{1,0x80410000},{1,0x80420000}};
static uint32_t actor=0x800a9228;
static unsigned ids[2]={23,23},modes[2]={2,2};
static unsigned cpu_index,cache_writes;
static uint32_t cache_addresses[2],cache_values[2];
static unsigned psx_mod_read_byte(uint32_t a) {assert(a==actor+0x1886);return cpu_index;}
static void psx_mod_write_word(uint32_t a,uint32_t v) {assert(cache_writes<2);cache_addresses[cache_writes]=a;cache_values[cache_writes++]=v;}
static int ready(unsigned p) {return loaded && modes[p]==2 && players[p].native_base;}
static void __real_func_80059890(CPUState *c) {real_calls++;c->pc=c->gpr[31];}
static uint32_t psx_mod_read_word(uint32_t a) {assert(a==0x800afa5c);return actor;}
static unsigned psx_mod_read_half(uint32_t a) {assert(a==actor+0x18);return ids[actor==0x800aaab4];}
static unsigned tekken3_jun_player_motion_mode(unsigned p) {assert(p<2);return modes[p];}
static void __real_func_8002CD7C(CPUState *c) {real_calls++;c->gpr[2]=0xbadcafe;c->pc=c->gpr[31];}
/* Extracted verbatim from the production C file by the test runner. */
#include "jun_cpu_command_wrapper.inc"
static void check(unsigned command,unsigned pc,int expected) {
    CPUState c={0};c.gpr[4]=command;c.gpr[31]=0x800618f0;c.pc=pc;
    int before=real_calls;__wrap_func_8002CD7C(&c);
    assert(c.pc==c.gpr[31]);assert(real_calls==before+!expected);
    assert(c.gpr[2]==(expected?patterns[(command&65535)-0xe000]:0xbadcafe));
}
int main(void) {
    for(unsigned p=0;p<2;p++) {
        actor=0x800a9228+p*0x188c;
        for(unsigned i=0;i<3;i++) {check(0xe000+i,0,1);check(0xffffe000+i,0x8002cd7c,1);}
        for(unsigned id=0;id<23;id++) {ids[p]=id;check(0xe000,0,0);}ids[p]=23;
        modes[p]=0;check(0xe000,0,0);modes[p]=2;
        players[p].native_base=0;check(0xe000,0,0);players[p].native_base=1;
        loaded=0;check(0xe000,0,0);loaded=1;
        check(0xdfff,0,0);check(0xe003,0,0);check(0xffff,0,0);check(0xc001,0,0);
        check(0xe000,0x8002cd80,0);
    }
    actor=0;check(0xe000,0,0);actor=0x800ac340;check(0xe000,0,0);
    for(unsigned p=0;p<2;p++)for(unsigned index=0;index<3;index++)for(unsigned jun=0;jun<2;jun++) {
        actor=0x800a9228+p*0x188c;ids[p]=jun?23:9;cpu_index=index==2?255:index;
        CPUState c={0};c.gpr[4]=actor;c.gpr[31]=0x8002c4cc;cache_writes=0;
        int before=real_calls;__wrap_func_80059890(&c);assert(real_calls==before+1);
        assert(cache_writes==(jun && index<2?2:0));
        if(cache_writes) {
            assert(cache_addresses[0]==0x8009f2e8+index*4);
            assert(cache_addresses[1]==0x8009f318+index*0x330+12);
            assert(cache_values[0]==players[p].alias_table && cache_values[1]==cache_values[0]);
        }
    }
    puts("Production CPU command wrapper: P1/P2, bounds, disabled/uninstalled and opponent isolation passed");
    puts("Production CPU alias-cache refresh: both actor slots, CPU indices and stock/disabled-index isolation passed");
}

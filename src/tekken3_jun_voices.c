/* Original local TTT1 PCM, routed by the game's character-voice dispatcher.
 * Playback runs on the emulation thread, before the existing host audio queue,
 * fade, master volume and resampler. No sample ROM is embedded in the binary. */
#include "psx_runtime.h"
#include "mod_plugins.h"
#include "psx_sha256.h"
#include "spu.h"
#include "tekken3_jun_assets.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern unsigned tekken3_jun_player_motion_mode(unsigned player);
extern void __real_func_80040C90(CPUState *cpu);
extern void __real_spu_render(int16_t *out, int frames);
extern void __real_spu_set_host_mix_volume(int sfx, int music);
extern void __real_spu_init(void);
extern int __real_spu_snapshot_read(const uint8_t *p, uint32_t len);

typedef struct { const unsigned char *pcm; uint32_t frames; } JunSample;
typedef struct { unsigned id, group; uint32_t pos, calls; } JunVoice;
static JunSample samples[12];
static JunVoice voices[2];
static unsigned char *bank;
static int attempted, loaded, sfx_gain = 100;
static uint32_t telemetry;

static uint32_t rd32(const unsigned char *p) {
    return p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int16_t rd16(const unsigned char *p) {
    return (int16_t)(p[0] | (unsigned)p[1]<<8);
}
static int jun(unsigned p) {
    return p<2 && tekken3_jun_player_motion_mode(p)==2;
}
static void stop_voices(void) { memset(voices,0,sizeof voices); }

static int load_bank(void) {
    if(attempted)return loaded;
    attempted=1;
    const char *root=tekken3_jun_asset_root();
    if(!root)return 0;
    char path[4096];
    if(snprintf(path,sizeof path,"%s/Jun-TTT1-voices.juv",root)>=(int)sizeof path)return 0;
    FILE *f=fopen(path,"rb");
    if(!f){fprintf(stderr,"Jun voices: missing private voice bank\n");return 0;}
    const unsigned size=527148;
    unsigned char *data=(unsigned char*)malloc(size);
    if(!data){fclose(f);return 0;}
    int ok=fread(data,1,size,f)==size && fgetc(f)==EOF;
    fclose(f);
    unsigned char digest[32];char hash[65];
    if(ok) {
        psx_sha256_compute(data,size,digest);
        for(unsigned i=0;i<32;i++)snprintf(hash+i*2,3,"%02x",digest[i]);
        ok=!strcmp(hash,"a83562e4efd6d6d0db0e23ed8a7a6cb4cb5972e74fad66d873d3122ef81a0be3");
    }
    ok=ok && rd32(data)==0x3156554a && rd32(data+4)==1 && rd32(data+8)==size &&
        rd32(data+12)==12 && rd32(data+16)==44100;
    uint32_t next=32+12*16;
    for(unsigned i=0;ok && i<12;i++) {
        const unsigned char *entry=data+32+i*16;
        uint32_t offset=rd32(entry+4),frames=rd32(entry+8);
        if(rd32(entry)!=160+i || offset!=next || offset>size || !frames || frames>(size-offset)/2) {
            ok=0;break;
        }
        next+=frames*2;
    }
    if(!ok || next!=size) {
        fprintf(stderr,"Jun voices: rejected corrupt or incompatible voice bank\n");
        free(data);return 0;
    }
    bank=data;
    for(unsigned i=0;i<12;i++) {
        samples[i].pcm=bank+rd32(bank+32+i*16+4);
        samples[i].frames=rd32(bank+32+i*16+8);
    }
    telemetry=psx_mod_alloc_guest_memory(80,16);
    if(telemetry)for(unsigned i=0;i<80;i+=4)psx_mod_write_word(telemetry+i,0);
    fprintf(stderr,"Jun voices: loaded 12 verified TTT1 samples; telemetry=%08X\n",telemetry);
    return loaded=1;
}

void tekken3_jun_voices_tick(void) {
    for(unsigned p=0;p<2;p++) {
        if(!jun(p) || psx_mod_read_half(0x800ae204)!=8)voices[p].group=0;
        else (void)load_bank();
        if(telemetry) {
            uint32_t dst=telemetry+p*32;
            JunVoice *v=&voices[p];
            psx_mod_write_word(dst,v->calls);
            psx_mod_write_word(dst+4,v->id);
            psx_mod_write_word(dst+8,v->group);
            psx_mod_write_word(dst+12,v->pos);
            psx_mod_write_word(dst+16,v->id>=160 && v->id<172?samples[v->id-160].frames:0);
        }
    }
    if(telemetry)psx_mod_write_word(telemetry+64,(uint32_t)sfx_gain);
}

void __wrap_func_80040C90(CPUState *cpu) {
    unsigned p=cpu->gpr[4], command=cpu->gpr[6]&65535;
    if((cpu->pc==0 || cpu->pc==0x80040c90) && jun(p) && load_bank()) {
        unsigned group=command>>12, index=command&4095, id;
        /* The native common/reaction records still use Jin's category sizes.
         * Translate within the matching Jun category; never into another bank.
         * Source Jun commands are already in range and retain their exact ID. */
        if(group==2)id=164+index%7;
        else if(group==3)id=160+index%3;
        else if(group==4)id=163;
        else if(group==5)id=171;
        else {cpu->pc=cpu->gpr[31];return;}
        JunVoice *v=&voices[p];
        v->id=id;v->group=group;v->pos=0;v->calls++;
        fprintf(stderr,"Jun voice: P%u command=%04X sample=%u\n",p+1,command,id);
        /* Only this actor's character cry is replaced. Shared hit, movement,
         * announcer and opponent calls keep the native sound path. */
        cpu->pc=cpu->gpr[31];return;
    }
    __real_func_80040C90(cpu);
}

void __wrap_spu_render(int16_t *out,int frames) {
    __real_spu_render(out,frames);
    if(!out || frames<=0 || !loaded)return;
    SpuGlobalState g;spu_get_global_state(&g);
    int audible=(g.ctrl&0xc000)==0xc000;
    int16_t main_volume[2]={(int16_t)spu_read(0x1f801db8),(int16_t)spu_read(0x1f801dba)};
    for(unsigned p=0;p<2;p++) {
        JunVoice *v=&voices[p];
        if(!v->group)continue;
        if(!jun(p) || psx_mod_read_half(0x800ae204)!=8){v->group=0;continue;}
        const JunSample *sample=&samples[v->id-160];
        for(int f=0;f<frames && v->pos<sample->frames;f++,v->pos++) {
            int32_t value=rd16(sample->pcm+v->pos*2);
            /* Match the PS1 voice mix level, with a short attack ramp. PCM
             * stays uncompressed; SFX and host master controls both apply. */
            int ramp=v->pos<220?(int)v->pos:220;
            value=value*sfx_gain/100*ramp/220/4;
            if(!audible)value=0;
            for(unsigned ch=0;ch<2;ch++) {
                int32_t mixed=(int32_t)out[f*2+ch]+value*main_volume[ch]/32768;
                out[f*2+ch]=(int16_t)(mixed>32767?32767:mixed< -32768?-32768:mixed);
            }
        }
        if(v->pos==sample->frames)v->group=0;
    }
}
void __wrap_spu_set_host_mix_volume(int sfx,int music) {
    sfx_gain=sfx<0?0:sfx>100?100:sfx;
    __real_spu_set_host_mix_volume(sfx,music);
}
void __wrap_spu_init(void) { stop_voices();__real_spu_init(); }
int __wrap_spu_snapshot_read(const uint8_t *p,uint32_t len) {
    int result=__real_spu_snapshot_read(p,len);
    if(result)stop_voices();
    return result;
}

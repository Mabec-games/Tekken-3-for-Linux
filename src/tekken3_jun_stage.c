/* Heavenly Garden: distinct stage 20, native TIMs and backdrop geometry.
 * Original stage 0..19 data, ROMs and music are never overwritten. */
#include "tekken3_jun_stage.h"
#include "mod_plugins.h"
#include "psx_sha256.h"
#include "psx_sdl.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

static unsigned char *textures, *mesh;
static uint32_t profiles, heights;
static int attempted, ready;
enum { TEXTURE_SIZE=323300, MESH_SIZE=23100 };

/* Bounded diagnostics for the reported non-Practice stage fallback. No save
 * data, input or gameplay state is changed; flush so an exit preserves it. */
static void stage_trace(const char *event, const char *format, ...) {
    static FILE *log;
    static unsigned count;
    static int opened;
    if(count>=256)return;
    if(!opened) {
        opened=1;
        const char *base=SDL_GetBasePath();char path[4096];
        if(base && snprintf(path,sizeof path,"%sjun-stage-trace.log",base)<(int)sizeof path)
            log=fopen(path,"w");
#if !defined(PSX_SDL3)
        SDL_free((void*)base);
#endif
    }
    if(!log)return;
    fprintf(log,"%u %s ready=%d mode=%u screen=%u stage=%u cache=%u/%u fighters=%u/%u players=%u cpu=%u owner=%u ",
        count++,event,ready,psx_mod_read_word(0x800afa88),psx_mod_read_word(0x800ae204),
        psx_mod_read_half(0x800adc84),psx_mod_read_byte(0x800afaa2),psx_mod_read_byte(0x800afaa3),
        psx_mod_read_half(0x800add5c),psx_mod_read_half(0x800add5e),
        psx_mod_read_byte(0x800afaa4),psx_mod_read_byte(0x800afaa7),psx_mod_read_byte(0x800b053e));
    va_list args;va_start(args,format);vfprintf(log,format,args);va_end(args);
    fputc('\n',log);fflush(log);
}

/* Resolve ownership at clean host loading boundaries. The live Survival
 * trace showed a valid Jun descriptor but no interpreted commit callback:
 * the compiled path selected Eddy (10/1). Do not rely on that callback. */
int tekken3_jun_stage_prepare(const char *site) {
    if(!ready)return 0;
    unsigned mode=psx_mod_read_word(0x800afa88);
    if(mode>5)return 0; /* Demo, Tekken Ball and Force own their arenas. */
    unsigned players=psx_mod_read_byte(0x800afaa4),side;
    if(players==1)side=psx_mod_read_byte(0x800afaa7);
    else if(players==2 && (mode==1 || mode==2 || mode==5))
        side=psx_mod_read_byte(0x800b053e);
    else return 0;
    if(side>1 || psx_mod_read_half(0x800add5c+side*2)!=23)return 0;
    unsigned prior=psx_mod_read_half(0x800adc84);
    psx_mod_write_half(0x800adc84,JUN_STAGE_ID);
    psx_mod_write_half(0x800add08,JUN_STAGE_MUSIC);
    psx_mod_write_byte(0x800afaa2,JUN_STAGE_ID);
    psx_mod_write_byte(0x800afaa3,JUN_STAGE_MUSIC);
    stage_trace("prepare","site=%s previous=%u owner_side=%u",site,prior,side);
    return 1;
}

typedef struct {uint32_t hi,lo;unsigned reg,offset;} StageReference;
static const StageReference refs[]={
    {0x800399a8,0x800399ac,2,28}, {0x80039e14,0x80039e18,3,28},
    {0x80039e50,0x80039e54,2,28}, {0x80039e74,0x80039e78,3,0},
    {0x80039e9c,0x80039ea0,3,0}, {0x80039ec4,0x80039ec8,3,0},
    {0x8003a170,0x8003a174,3,0}
};

static void copy_guest(uint32_t dst,uint32_t src,unsigned n) {
    for(unsigned i=0;i<n;i++)psx_mod_write_byte(dst+i,psx_mod_read_byte(src+i));
}
static void patch(uint32_t addr,uint32_t expected,uint32_t value) {
    if(psx_mod_read_word(addr)==expected)psx_mod_write_code_word(addr,value);
}
static void reference(const StageReference *r) {
    uint32_t target=profiles+r->offset;
    patch(r->hi,0x3c008009|(r->reg<<16),0x3c000000|(r->reg<<16)|(target>>16));
    patch(r->lo,0x24000000|(r->reg<<21)|(r->reg<<16)|(0x6c5c+r->offset),
          0x34000000|(r->reg<<21)|(r->reg<<16)|(target&65535));
}
static int read_asset(const char *root,const char *name,unsigned size,
                      const char *expected,unsigned char **result) {
    char path[4096],actual[65];unsigned char digest[32];
    int n=snprintf(path,sizeof path,"%smods/jun-heavenly-garden/%s",root,name);
    if(n<0 || n>=(int)sizeof path)return 0;
    FILE *f=fopen(path,"rb");if(!f)return 0;
    unsigned char *p=malloc(size);
    int ok=p && fread(p,1,size,f)==size && fgetc(f)==EOF;fclose(f);
    if(ok) {
        psx_sha256_compute(p,size,digest);
        for(unsigned i=0;i<32;i++)snprintf(actual+i*2,3,"%02x",digest[i]);
        ok=!strcmp(actual,expected);
    }
    if(!ok){free(p);return 0;}
    *result=p;return 1;
}

unsigned tekken3_jun_stage_initialize(void) {
    if(attempted)return ready?JUN_STAGE_ID:8;
    attempted=1;
    /* Verify the exact US executable before extending any table. */
    for(unsigned i=0;i<sizeof refs/sizeof *refs;i++) {
        const StageReference *r=&refs[i];
        if(psx_mod_read_word(r->hi)!=(0x3c008009|(r->reg<<16)) ||
           psx_mod_read_word(r->lo)!=(0x24000000|(r->reg<<21)|(r->reg<<16)|(0x6c5c+r->offset)))goto invalid;
    }
    if(psx_mod_read_word(0x8006d5e4)!=0x3c038002 ||
       psx_mod_read_word(0x8006d5f4)!=0x24635138 ||
       psx_mod_read_word(0x8004f724)!=0x3c02800b ||
       psx_mod_read_word(0x8004f728)!=0xa444dc84)goto invalid;
    const char *base=SDL_GetBasePath();if(!base)goto invalid;
    int loaded=read_asset(base,"Heavenly-Garden.arc",TEXTURE_SIZE,
        "ffa1aacdf24d046269b8c125b6a22c9cd42520e11b09d68be8f375fb49278401",&textures) &&
        read_asset(base,"Heavenly-Garden.mesh",MESH_SIZE,
        "65b9f3e24144097066fe85fcd7691b42ae97a843bb50215e28fa46550cef3633",&mesh);
#if !defined(PSX_SDL3)
    SDL_free((void*)base);
#endif
    if(!loaded)goto invalid;
    profiles=psx_mod_alloc_guest_memory(0x400,16);if(!profiles)goto invalid;
    heights=profiles+0x300;
    /* Include the prefix row because four getters use (stage+1)*28. */
    copy_guest(profiles,0x80096c5c,21*28);
    copy_guest(profiles+21*28,0x80096c78+4*28,28);
    /* Neutral character lighting, separate from the new backdrop palette. */
    psx_mod_write_word(profiles+21*28+4,0x00808080);
    psx_mod_write_word(profiles+21*28+8,0x00c8c8c8);
    copy_guest(heights,0x80025138,20*4);
    copy_guest(heights+20*4,0x80025138+4*4,4);
    ready=1;tekken3_jun_stage_tick();
    stage_trace("initialize","profiles=%08X textures=validated mesh=validated",profiles);
    fprintf(stderr,"Jun stage: Heavenly Garden registered as stage 20, native textures, Jin BGM 16\n");
    return JUN_STAGE_ID;
invalid:
    free(textures);free(mesh);textures=mesh=NULL;
    fprintf(stderr,"Jun stage: pack or executable validation failed; keeping Jin stage 8\n");
    return 8;
}

void tekken3_jun_stage_tick(void) {
    if(!ready)return;
    static uint32_t previous[5];
    uint32_t current[]={psx_mod_read_word(0x800afa88),psx_mod_read_word(0x800ae204),
        psx_mod_read_word(0x800add5c),psx_mod_read_half(0x800adc84),psx_mod_read_word(0x800b0460)};
    if(memcmp(previous,current,sizeof current)) {
        memcpy(previous,current,sizeof current);
        stage_trace("state","render_stage=%u commit_opcode=%08X",current[4],psx_mod_read_word(0x8004f728));
    }
    for(unsigned i=0;i<sizeof refs/sizeof *refs;i++)reference(&refs[i]);
    patch(0x8006d5e4,0x3c038002,0x3c030000|(heights>>16));
    patch(0x8006d5f4,0x24635138,0x34630000|(heights&65535));
}

int tekken3_jun_stage_load(CPUState *cpu) {
    uint32_t trace_ret=cpu->gpr[31];
    int stage_request=trace_ret==0x800368b4 || trace_ret==0x80036924 ||
                      trace_ret==0x800369f0 || trace_ret==0x80036a60;
    if(stage_request)stage_trace("request","pc=%08X caller=%08X record=%u dst=%08X",
        cpu->pc,trace_ret,cpu->gpr[5],cpu->gpr[4]);
    if(!ready || (cpu->pc && cpu->pc!=0x80052ad0) ||
       psx_mod_read_half(0x800adc84)!=JUN_STAGE_ID)return 0;
    unsigned mode=psx_mod_read_word(0x800afa88);
    if(mode==7 || mode==8)return 0; /* Mode-owned stages always stay native. */
    uint32_t ret=cpu->gpr[31],record=cpu->gpr[5],size=0;
    const unsigned char *data=NULL;
    if(record==JUN_STAGE_ID+34 && (ret==0x800368b4 || ret==0x800369f0)) {
        data=textures;size=TEXTURE_SIZE;
    } else if(record==JUN_STAGE_ID+54 && (ret==0x80036924 || ret==0x80036a60)) {
        data=mesh;size=MESH_SIZE;
    }
    if(!data)return 0;
    uint32_t dst=cpu->gpr[4],physical=dst&0x1fffffff;
    if(physical<0x10000 || physical>0x200000-size) {
        fprintf(stderr,"Jun stage: invalid native load destination %08X\n",dst);
        cpu->gpr[2]=0xffffffff;cpu->pc=ret;return 1;
    }
    for(unsigned i=0;i<size;i+=4) {
        uint32_t value;memcpy(&value,data+i,4);psx_mod_write_word(dst+i,value);
    }
    /* This synchronous host copy replaces a synchronous native CD request.
     * Keep the exact buffer footprint and successful return value (zero). */
    cpu->gpr[2]=0;cpu->pc=ret;
    stage_trace("loaded","kind=%s caller=%08X bytes=%u dst=%08X",data==textures?"textures":"mesh",ret,size,dst);
    fprintf(stderr,"Jun stage: loaded Heavenly Garden %s into %08X\n",data==textures?"textures":"mesh",dst);
    return 1;
}

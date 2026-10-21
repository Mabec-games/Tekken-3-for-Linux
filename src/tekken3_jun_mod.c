/* Local, opt-in import probe. Assets are loaded from an explicit private
 * directory and never embedded in or distributed with the executable. */
#include "mod_plugins.h"
#include "psx_runtime.h"
#include "gpu_render.h"
#include "gpu.h"
#include "psx_sha256.h"
#include "psx_sdl.h"
#include "tekken3_jun_assets.h"
#include "tekken3_jun_costumes.h"
#include "tekken3_outfits.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned char *model, *textures;
    uint32_t *relocations, guest;
} JunCostume;
static JunCostume costumes[JUN_COSTUME_COUNT];
static uint32_t guest, control;
static uint32_t arena[2];
static int attempted;
static uint32_t original_header[2][384], original_base[2];
static int initializing;
static int face_variant[2]={-1,-1};
static unsigned player_outfit(unsigned player) {
    unsigned outfit=psx_mod_read_half(0x800a923c+player*0x188c)&3;
    return outfit<JUN_COSTUME_COUNT?outfit:0;
}
static int installed_outfit(uint32_t base) {
    uint32_t first=psx_mod_read_word(base+24);
    for(unsigned i=0;i<JUN_COSTUME_COUNT;i++)
        if(costumes[i].guest && first==costumes[i].guest+0x6c8)return (int)i;
    return -1;
}
const char *tekken3_jun_asset_root(void) {
    const char *override=getenv("TEKKEN3_JUN_ASSETS");
    if(override && *override)return override;
    static char path[4096];
    if(!path[0]) {
        const char *base=SDL_GetBasePath();
        if(!base)return NULL;
        int n=snprintf(path,sizeof path,"%smods/jun",base);
#if !defined(PSX_SDL3)
        SDL_free((void*)base);
#endif
        if(n<0 || n>=(int)sizeof path){path[0]=0;return NULL;}
    }
    return path;
}
extern void tekken3_jun_combat_tick(void);
extern void tekken3_jun_selector_tick(void);
extern void tekken3_jun_voices_tick(void);
extern int tekken3_jun_roster_enabled(void);
static int jun_player(unsigned player) {
    return tekken3_jun_roster_enabled()?psx_mod_read_half(0x800a9240+player*0x188c)==23:
        player==0 && psx_mod_read_byte(0x80098106)==9;
}
void tekken3_jun_select(int enabled) {
    if(!control)return;
    psx_mod_write_byte(control,enabled?1:0);
    psx_mod_write_byte(control+12,enabled?2:0);
    if(!enabled)tekken3_jun_combat_tick();
    fprintf(stderr,"Jun selector: import %s\n",enabled?"active":"inactive");
}

void tekken3_jun_before_init(uint32_t model) {
    initializing++;
    for(unsigned p=0;p<2;p++)if (model==original_base[p] && guest && installed_outfit(model)>=0) {
        for(unsigned i=0;i<384;i++) psx_mod_write_word(model+i*4,original_header[p][i]);
        fprintf(stderr,"Jun probe: restored stock header before actor initialization\n");
    }
}
void tekken3_jun_after_init(void) { if(initializing>0) initializing--; }

static uint32_t word(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int verified_asset(const void *data, size_t size, const char *expected) {
    unsigned char hash[32]; char actual[65];
    psx_sha256_compute((const uint8_t*)data,size,hash);
    for(unsigned i=0;i<32;i++) snprintf(actual+i*2,3,"%02x",hash[i]);
    return strcmp(actual,expected)==0;
}
static int read_asset(const char *root, const char *name, void *data, size_t size) {
    char path[4096];
    if (snprintf(path,sizeof(path),"%s/%s",root,name)>=(int)sizeof(path)) return 0;
    FILE *f=fopen(path,"rb");
    if (!f) return 0;
    int ok=fread(data,1,size,f)==size && fgetc(f)==EOF;
    fclose(f); return ok;
}
static void load_assets(void) {
    const char *root=tekken3_jun_asset_root();
    if (!root || !*root) return;
    for(unsigned c=0;c<JUN_COSTUME_COUNT;c++) {
        JunCostume *a=&costumes[c];const JunCostumeSpec *s=&jun_costume_specs[c];
        char name[64];
        a->model=malloc(s->model_size);a->textures=malloc(s->texture_size);
        a->relocations=malloc(s->relocation_count*4);
        if(!a->model || !a->textures || !a->relocations)goto invalid;
        snprintf(name,sizeof name,"Jun-TTT1-arcade-P%u.3dm",c+1);
        if(!read_asset(root,name,a->model,s->model_size) || !verified_asset(a->model,s->model_size,s->model_sha))goto invalid;
        snprintf(name,sizeof name,"Jun-TTT1-arcade-P%u.tim",c+1);
        if(!read_asset(root,name,a->textures,s->texture_size) || !verified_asset(a->textures,s->texture_size,s->texture_sha))goto invalid;
        snprintf(name,sizeof name,"Jun-TTT1-arcade-P%u.relocs",c+1);
        if(!read_asset(root,name,a->relocations,s->relocation_count*4) || !verified_asset(a->relocations,s->relocation_count*4,s->relocation_sha))goto invalid;
        if(word(a->model)!=30 || word(a->model+8)!=0x4b4d4433 || word(a->model+16)!=0x6a0)goto invalid;
        for(unsigned i=0;i<s->relocation_count;i++) {
            uint32_t r=a->relocations[i];
            if((r&3) || r>s->model_size-4 || !word(a->model+r) || word(a->model+r)>=s->model_size)goto invalid;
        }
    }
    control=psx_mod_alloc_guest_memory(32,16);
    arena[0]=psx_mod_alloc_gpu_dma_memory(262144,16);
    arena[1]=psx_mod_alloc_gpu_dma_memory(262144,16);
    if (!control || !arena[0] || !arena[1])goto invalid;
    for(unsigned c=0;c<JUN_COSTUME_COUNT;c++) {
        JunCostume *a=&costumes[c];const JunCostumeSpec *s=&jun_costume_specs[c];
        a->guest=psx_mod_alloc_guest_memory(s->model_size,16);
        if(!a->guest)goto invalid;
        for(unsigned i=0;i<s->model_size;i+=4)psx_mod_write_word(a->guest+i,word(a->model+i));
        for(unsigned i=0;i<s->relocation_count;i++) {
            uint32_t r=a->relocations[i];psx_mod_write_word(a->guest+r,word(a->model+r)+a->guest);
        }
        fprintf(stderr,"Jun outfit %u: model=%08X bytes=%u\n",c+1,a->guest,s->model_size);
    }
    guest=costumes[0].guest;
    tekken3_outfits_set_character_available(23,1);
    fprintf(stderr,"Jun probe: control=%08X model=%08X; set control byte to 1 to test\n",control,guest);
    return;
invalid:
    for(unsigned c=0;c<JUN_COSTUME_COUNT;c++) {
        free(costumes[c].model);free(costumes[c].textures);free(costumes[c].relocations);
        memset(&costumes[c],0,sizeof costumes[c]);
    }
    control=guest=0;
    fprintf(stderr,"Jun import: all three verified arcade outfits are required; run the local importer\n");
}
int tekken3_jun_uses_arcade_renderer(uint32_t address) {
    if (!guest || psx_mod_read_byte(control)!=1) return 0;
    uint32_t p=psx_mod_read_word(address);
    for(unsigned c=0;c<JUN_COSTUME_COUNT;c++)
        if(p>=costumes[c].guest && p<costumes[c].guest+jun_costume_specs[c].model_size)return 1;
    return 0;
}
unsigned tekken3_jun_player_motion_mode(unsigned player) {
    return player<2 && guest && original_base[player] && psx_mod_read_byte(control)==1 && !initializing &&
        jun_player(player) &&
        psx_mod_read_word(0x8009bd28u+player*4)==original_base[player] &&
        installed_outfit(original_base[player])==(int)player_outfit(player)
        ? psx_mod_read_byte(control+12) : 0;
}
unsigned tekken3_jun_motion_mode(void) {return tekken3_jun_player_motion_mode(0);}
static uint16_t half(const unsigned char *p) { return p[0] | (uint16_t)p[1]<<8; }
#include "tekken3_jun_texture_layout.h"
static void upload_textures(unsigned player) {
    unsigned outfit=player_outfit(player);
    const unsigned char *textures=costumes[outfit].textures;
    unsigned texture_size=jun_costume_specs[outfit].texture_size;
    face_variant[player]=-1;
    for (unsigned o=0;o+8<texture_size;) {
        if (word(textures+o)!=16) return;
        unsigned flags=word(textures+o+4);o+=8;
        if (flags&8) {
            unsigned n=word(textures+o);
            gr_vram_transfer_in(half(textures+o+4),504+player*4+half(textures+o+6),
                half(textures+o+8),half(textures+o+10),(const uint16_t*)(textures+o+12));
            o+=n;
        }
        unsigned n=word(textures+o);
        unsigned x=half(textures+o+4), y=half(textures+o+6);
        const JunTextureTile *tile=jun_texture_tile(outfit,flags&3,x,y);
        if(!tile)return; /* Asset hashes and the offline UV audit bind this table. */
        gr_vram_transfer_in(384+tile->dx,player*256+tile->dy,
            half(textures+o+8),half(textures+o+10),(const uint16_t*)(textures+o+12));
        o+=n;
    }
}
void tekken3_jun_face(unsigned player,unsigned variant) {
    if(player>1 || variant>1 || !guest || face_variant[player]==(int)variant)return;
    unsigned outfit=player_outfit(player);
    const unsigned char *textures=costumes[outfit].textures;
    unsigned texture_size=jun_costume_specs[outfit].texture_size;
    /* Original Jun face table 801945D8[46]: destination (16,64),
     * size (16,64); expression 1 comes from (0,0). Expression 0 restores
     * the original destination, which the arcade backed up at (192,64). */
    for(unsigned o=0;o+8<texture_size;) {
        if(word(textures+o)!=16)return;
        unsigned flags=word(textures+o+4);o+=8;
        if(flags&8)o+=word(textures+o);
        unsigned n=word(textures+o),x=half(textures+o+4),y=half(textures+o+6);
        if(x==(variant?0:16) && y==(variant?0:64) && half(textures+o+8)==16 && half(textures+o+10)==64) {
            const JunTextureTile *tile=jun_texture_tile(outfit,1,16,64);
            if(!tile)return;
            gr_vram_transfer_in(384+tile->dx,player*256+tile->dy,16,64,(const uint16_t*)(textures+o+12));
            face_variant[player]=(int)variant;return;
        }
        o+=n;
    }
}
static void ensure_textures(unsigned player) {
    /* Native round/replay loads and PS1 save states can restore the loader's
     * Jin textures while retaining our model/packet pointers. */
    unsigned outfit=player_outfit(player);
    const unsigned char *textures=costumes[outfit].textures;
    unsigned texture_size=jun_costume_specs[outfit].texture_size;
    /* Host/CPU uploads update this shadow immediately. Do not call the GL
     * readback facade every VBlank: it downloads the entire framebuffer. */
    const uint16_t *vram=gpu_get_vram();
    if(!vram)return;
    /* Check every immutable tile, not just the first face. A late loading
     * thumbnail can overwrite the secondary page after model installation.
     * Read the CPU shadow only; this must never force a GPU readback. */
    for(unsigned o=0;o+8<texture_size;) {
        if(word(textures+o)!=16)return;
        unsigned flags=word(textures+o+4);o+=8;
        if(flags&8)o+=word(textures+o);
        unsigned n=word(textures+o),x=half(textures+o+4),y=half(textures+o+6);
        unsigned w=half(textures+o+8),h=half(textures+o+10);
        const JunTextureTile *tile=jun_texture_tile(outfit,flags&3,x,y);
        if(!tile)return;
        if(!(x==16 && y==64))for(unsigned row=0;row<h;row++) {
            const uint16_t *live=vram+(player*256+tile->dy+row)*1024+384+tile->dx;
            if(memcmp(live,textures+o+12+row*w*2,w*2)) {
                int expression=face_variant[player];
                upload_textures(player);
                if(expression>=0)tekken3_jun_face(player,(unsigned)expression);
                return;
            }
        }
        o+=n;
    }
}
/* Build PS1 GPU packets from the donor's material/UV stream. The arcade
 * renderer supplies positions and lighting into these packet templates. */
static uint32_t make_packets(uint32_t bundle,uint32_t out,unsigned player) {
    uint32_t m=psx_mod_read_word(bundle+16);
    uint32_t uv=m+psx_mod_read_word(m);
    uint32_t src=uv+psx_mod_read_half(uv);
    static const unsigned size[4]={32,40,40,52};
    static const unsigned opcode[4]={0x24,0x2c,0x34,0x3c};
    static const unsigned voff[4][4]={{12,20,28,0},{12,20,28,36},{12,24,36,0},{12,24,36,48}};
    for(unsigned kind=0;kind<4;kind++) {
        unsigned count=psx_mod_read_byte(src++),nv=(kind&1)?4:3;
        for(unsigned i=0;i<count;i++) {
            unsigned material=psx_mod_read_byte(src++);
            uint32_t mat=psx_mod_read_word(m+4+material*4);
            for(unsigned j=0;j<size[kind];j+=4) psx_mod_write_word(out+j,0);
            psx_mod_write_word(out+4,(opcode[kind]<<24)|0x808080);
            if(kind>=2) {
                psx_mod_write_word(out+16,0x808080);psx_mod_write_word(out+28,0x808080);
                if(nv==4) psx_mod_write_word(out+40,0x808080);
            }
            const JunTextureTile *tile=NULL;
            for(unsigned j=0;j<nv;j++) {
                unsigned idx=psx_mod_read_byte(src++);
                uint32_t v=psx_mod_read_half(uv+2+idx*2);
                unsigned page=mat>>16, mode=(page>>7)&3, ppw=4>>mode;
                unsigned x=(page&15)*64+(v&255)/ppw;
                unsigned y=(v>>8)+((page&16)?256:0);
                /* Each verified polygon lies within one TIM tile. Move its
                 * UVs with that tile, preserving texel sub-word coordinates.
                 * Never occupy the shared effects page or command/font data. */
                if(j==0)tile=jun_texture_tile(player_outfit(player),mode,x,y);
                if(!tile)return out;
                v=((tile->dx%64+x-tile->x)*ppw+(v&255)%ppw)|
                    ((tile->dy+y-tile->y)<<8);
                if(j==0) v|=((mat&0xffff)+0x7e00+player*256)<<16;
                if(j==1) v|=((page&~31u)| (6+tile->dx/64) | (player*16))<<16;
                psx_mod_write_word(out+voff[kind][j],v);
            }
            out+=size[kind];
        }
    }
    return out;
}
static int32_t mul12(int32_t a,int32_t b) { return (a*b)>>12; }
static void accessory_rotation(uint32_t destination,uint32_t row) {
    int32_t s[3],c[3];
    for(unsigned i=0;i<3;i++) {
        unsigned angle=psx_mod_read_word(row+28+i*4);
        uint32_t table=0x8001e8c4+((angle>>3)&0x1ffe);
        s[i]=(int16_t)psx_mod_read_half(table);
        c[i]=(int16_t)psx_mod_read_half(table+0x800);
    }
    int32_t a=mul12(c[0],c[2]),b=mul12(c[0],s[2]);
    int32_t d=mul12(s[0],c[2]),e=mul12(s[0],s[2]);
    int32_t matrix[9]={mul12(c[1],c[2]),mul12(d,s[1])-b,e+mul12(a,s[1]),
        mul12(c[1],s[2]),a+mul12(e,s[1]),mul12(b,s[1])-d,
        -s[1],mul12(s[0],c[1]),mul12(c[0],c[1])};
    for(unsigned i=0;i<9;i++) psx_mod_write_half(destination+i*2,(uint16_t)matrix[i]);
}
extern void __real_func_80037CBC(CPUState *cpu);
void __wrap_func_80037CBC(CPUState *cpu) {
    /* The native accessory solver initializes its angles from Jin's empty
     * accessory slots and overwrites our matrices on the next frame. Jun's
     * donor hair and bow have their own rest rotations. Keep these rigid
     * until the donor's secondary-motion solver is ported. */
    if(cpu->pc==0 || cpu->pc==0x80037cbc) {
        uint32_t actor=cpu->gpr[4];unsigned bone=cpu->gpr[5];
        for(unsigned p=0;p<2;p++) if(actor==0x800a9228+p*0x188c &&
                bone>=19 && bone<=22 && tekken3_jun_player_motion_mode(p)) {
            unsigned row=psx_mod_read_byte(0x8001a05c+bone);
            accessory_rotation(actor+0xf74+bone*32,original_base[p]+24+row*56);
            cpu->pc=cpu->gpr[31];return;
        }
    }
    __real_func_80037CBC(cpu);
}
static void rebuild_packets(uint32_t base,unsigned player) {
    const uint32_t actor=0x800a9228+player*0x188c;
    uint32_t next=arena[player];
    for(unsigned i=19;i<=22;i++) {
        unsigned row=psx_mod_read_byte(0x8001a05c+i),bone=psx_mod_read_byte(0x8001a074+i);
        uint32_t part=actor+0x4f0+i*40;
        if(!psx_mod_read_word(base+24+row*56)) {
            psx_mod_write_word(part,0);continue;
        }
        unsigned parent=psx_mod_read_word(base+24+row*56+24);
        if(parent>=24) {psx_mod_write_word(part,0);continue;}
        psx_mod_write_word(part,2);
        psx_mod_write_word(part+4,actor+0x8f4+bone*68);
        psx_mod_write_word(part+8,base+16+row*56);
        psx_mod_write_word(part+12,0);
        psx_mod_write_word(actor+0x8f4+bone*68+64,psx_mod_read_word(actor+0x4f4+parent*40));
        accessory_rotation(actor+0xf74+bone*32,base+24+row*56);
    }
    for(unsigned i=1;i<24;i++) {
        uint32_t part=actor+0x4f0+i*40;
        if(!psx_mod_read_word(part)) continue;
        for(unsigned mesh=0;mesh<2;mesh++) {
            uint32_t bundle=psx_mod_read_word(part+8+mesh*4);
            if(!bundle) continue;
            for(unsigned frame=0;frame<2;frame++) {
                psx_mod_write_word(part+24+mesh*8+frame*4,next);
                next=make_packets(bundle,next,player);
            }
        }
        unsigned row=psx_mod_read_byte(0x8001a05c+i),bone=psx_mod_read_byte(0x8001a074+i);
        uint32_t pos=actor+0xf88+bone*32;
        psx_mod_write_word(pos,psx_mod_read_word(base+24+row*56+12));
        psx_mod_write_word(pos+4,psx_mod_read_word(base+24+row*56+16));
        psx_mod_write_word(pos+8,psx_mod_read_word(base+24+row*56+20));
    }
    fprintf(stderr,"Jun probe: P%u prepared %u packet bytes\n",player+1,next-arena[player]);
    upload_textures(player);
}
static void player_tick(unsigned player) {
    if (!jun_player(player)) return;
    /* Early fight substates still use fighter VRAM as a loading scratchpad.
     * Wait for the native actor/stage initialization before installing donor
     * packets and textures, otherwise a later MoveImage copies them on screen. */
    if(psx_mod_read_word(0x800ae204)!=8 || psx_mod_read_half(0x800ae224)<6)return;
    uint32_t base=psx_mod_read_word(0x8009bd28u+player*4);
    if (base<0x80100000 || base>0x801f8000 ||
        psx_mod_read_word(base)!=27 || psx_mod_read_word(base+8)!=0x4b4d4433) return;
    unsigned outfit=player_outfit(player);
    uint32_t selected=costumes[outfit].guest;
    int installed=installed_outfit(base);
    if (installed==(int)outfit) {
        /* Mirror matches may share a model header, but GPU packets and VRAM
         * pages belong to the individual actor. */
        if(original_base[player]!=base) {
            original_base[player]=base;
            memcpy(original_header[player],original_header[1-player],sizeof original_header[player]);
        }
        uint32_t packet=psx_mod_read_word(0x800a9228+player*0x188c+0x4f0+40+24);
        if(packet && (packet<arena[player] || packet>=arena[player]+262144))rebuild_packets(base,player);
        ensure_textures(player);
        return;
    }
    if(installed>=0 && original_base[player]==base)
        for(unsigned i=0;i<384;i++)psx_mod_write_word(base+i*4,original_header[player][i]);
    /* Exact Jin punch-costume envelope. No other fighter or costume qualifies. */
    if (psx_mod_read_word(base+24)!=base+0x620 ||
        psx_mod_read_word(base+80)!=base+0x98c ||
        psx_mod_read_word(base+24+19*56)!=base+0x5714) return;
    if (psx_mod_read_byte(control)==2) {
        /* Relocation-only control: same live Jin asset, different storage. */
        for (unsigned i=0;i<26364;i+=4) {
            uint32_t v=psx_mod_read_word(base+i);
            if (v>=base && v<base+26364) v=v-base+guest;
            psx_mod_write_word(guest+i,v);
        }
        for (unsigned i=0;i<1536;i+=4)
            psx_mod_write_word(base+i,psx_mod_read_word(guest+i));
        psx_mod_write_word(control+4,base);
        psx_mod_write_word(control+8,psx_mod_read_word(control+8)+1);
        fprintf(stderr,"Jun probe: relocation-only Jin control at %08X\n",base);
        return;
    }
    /* Remove empty source placeholders 2, 5 and 28. Active-node parent
     * indices are unchanged. Keep the PS1 table's 27 rows and end marker. */
    static const unsigned rows[27]={0,1,3,4,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,29};
    original_base[player]=base;
    for(unsigned i=0;i<384;i++) original_header[player][i]=psx_mod_read_word(base+i*4);
    psx_mod_write_word(base+16,selected+0x6a0);
    for (unsigned i=0;i<27;i++)
        for (unsigned j=0;j<56;j+=4)
            psx_mod_write_word(base+24+i*56+j,psx_mod_read_word(selected+24+rows[i]*56+j));
    rebuild_packets(base,player);
    psx_mod_write_word(control+4,base);
    psx_mod_write_word(control+8,psx_mod_read_word(control+8)+1);
    fprintf(stderr,"Jun probe: P%u Jin model header replaced at %08X\n",player+1,base);
    fprintf(stderr,"Jun outfit: P%u selected arcade P%u\n",player+1,outfit+1);
}
static void jun_tick(void) {
    if (!psx_mod_game_started()) return;
    if (!attempted) { attempted=1; load_assets(); }
    if(guest)tekken3_jun_selector_tick();
    if(guest)tekken3_jun_voices_tick();
    if (!guest || initializing || !psx_mod_read_byte(control)) return;
    for(unsigned player=0;player<2;player++)player_tick(player);
    tekken3_jun_combat_tick();
}
PSX_MOD_CONSTRUCTOR(register_jun_probe) {
    (void)psx_mod_register_vblank_plugin("tekken3.jun-probe",jun_tick);
}

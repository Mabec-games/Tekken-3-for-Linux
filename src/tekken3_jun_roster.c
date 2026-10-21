/* SLUS-00402's opt-in extra roster entry. 21 remains the Force enemies,
 * 22 remains the empty-selection sentinel; Jun owns character ID 23 and
 * model IDs 52..54. Private guest tables extend the stock tables without moving
 * their neighbours. Original disc data is never changed. */
#include "mod_plugins.h"
#include "psx_runtime.h"
#include "gpu_render.h"
#include "psx_sha256.h"
#include "tekken3_jun_assets.h"
#include "tekken3_jun_stage.h"
#include "tekken3_jun_ui_palette.h"
#include "tekken3_jun_ui_layout.h"
#include "tekken3_jun_ui_texture.h"
#include "tekken3_outfits.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { JUN_ID=23, JUN_MODEL=52, ROSTER_COUNT=22 };
static uint32_t metadata,model_map,model_sizes,team_table,ui_color,body_profiles,face_profiles,force_bosses;
static uint32_t portrait_bank,usage_mask,cpu_profiles;
static unsigned icon_screen=~0u;
static unsigned char *ui;
static uint16_t name_pixels[96];
static uint16_t loading_pixels[16*58];
static JunUiPalette selector_palette, loading_palette, grey_palette;
static JunUiTexture selector_texture,loading_texture;
static unsigned grey_screen=~0u;
static uint16_t grey_colors[256];
static uint32_t stock_icon_uv,stock_icon_page;
static uint32_t ui_size,ui_offsets[5],ui_lengths[5];
static int initialized,attempted,enabled=-1;
extern void tekken3_jun_select(int enabled);
extern void __real_func_80052938(CPUState*);
extern void __real_func_80052940(CPUState*);
extern void __real_func_80052948(CPUState*);
extern void __real_func_8004B790(CPUState*);
extern void __real_func_8004B928(CPUState*);
extern void __real_func_80031BFC(CPUState*);
extern int tekken3_anna_portrait_decode(CPUState*);
extern void __real_func_80052AD0(CPUState*);
extern void __real_func_80052958(CPUState*);
extern void __real_func_80052990(CPUState*);
extern void __real_func_8006BF20(CPUState*);
extern void __real_func_8003626C(CPUState*);
extern void __real_func_80036294(CPUState*);
extern void __real_func_800362C4(CPUState*);
extern void __real_func_8003F044(CPUState*);
extern void __real_func_800513C0(CPUState*);
extern void __real_func_80051464(CPUState*);
extern void __real_func_8005155C(CPUState*);
extern void __real_func_80051660(CPUState*);

int tekken3_jun_roster_enabled(void) {
    if(enabled<0) {const char *p=getenv("TEKKEN3_JUN_ROSTER");enabled=!p || strcmp(p,"0");}
    return enabled && initialized;
}
static uint32_t u32(const unsigned char *p) {return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint16_t u16(const unsigned char *p) {return p[0]|(uint16_t)p[1]<<8;}
static void copy_guest(uint32_t dst,uint32_t src,unsigned n) {
    for(unsigned i=0;i<n;i++)psx_mod_write_byte(dst+i,psx_mod_read_byte(src+i));
}
static void copy_host(uint32_t dst,const unsigned char *src,unsigned n) {
    for(unsigned i=0;i<n;i++)psx_mod_write_byte(dst+i,src[i]);
}
static void patch(uint32_t address,uint32_t expected,uint32_t replacement) {
    uint32_t actual=psx_mod_read_word(address);
    if(actual==expected)psx_mod_write_code_word(address,replacement);
}
static void indirect(uint32_t address,uint32_t expected) {
    unsigned offset=expected&65535;
    uint32_t target=offset==0x7d40?metadata:offset==0x58c4?model_map:offset==0x5a9c?model_sizes:team_table;
    /* A LUI replaces ADDIU without introducing a MIPS load-delay hazard.
     * Each extended table therefore has a 64 KiB aligned guest address. */
    patch(address,expected,0x3c000000u|(expected&0x001f0000u)|(target>>16));
}
static void immediate(uint32_t address,unsigned expected,unsigned replacement) {
    uint32_t op=psx_mod_read_word(address);
    if((op&65535)==expected)patch(address,op,(op&0xffff0000)|replacement);
}
#include "tekken3_jun_cpu.h"
static int load_ui(void) {
    const char *root=tekken3_jun_asset_root();char path[4096];
    if(!root || snprintf(path,sizeof path,"%s/Jun-T3-ui.jui",root)>=(int)sizeof path)return 0;
    FILE *f=fopen(path,"rb");if(!f)return 0;
    unsigned char h[56];int ok=fread(h,1,sizeof h,f)==sizeof h;
    if(!ok || u32(h)!=0x3149554a || u32(h+4)!=1 || u32(h+8)!=5 ||
       u32(h+12)!=40576){fclose(f);return 0;}
    ui_size=u32(h+12);ui=malloc(ui_size);if(!ui){fclose(f);return 0;}
    memcpy(ui,h,sizeof h);ok=fread(ui+56,1,ui_size-56,f)==ui_size-56 && fgetc(f)==EOF;fclose(f);
    for(unsigned i=0;ok && i<5;i++) {
        unsigned o=u32(h+16+i*8),n=u32(h+20+i*8);
        static const unsigned widths[5]={126,32,32,32,32},heights[5]={252,68,58,34,29};
        ok=o>=56 && o<=ui_size && n<=ui_size-o && n==544+widths[i]*heights[i] &&
           u32(ui+o)==16 && u32(ui+o+4)==9 && u32(ui+o+8)==524 &&
           u16(ui+o+540)==widths[i]/2 && u16(ui+o+542)==heights[i];
        ui_offsets[i]=o;ui_lengths[i]=n;
    }
    if(!ok){free(ui);ui=NULL;return 0;}
    unsigned char digest[32];char hex[65];
    psx_sha256_compute(ui,ui_size,digest);
    for(unsigned i=0;i<32;i++)snprintf(hex+i*2,3,"%02x",digest[i]);
    if(strcmp(hex,"f4c2f82a5712cbb35b4f038e09b8c0dea57b3b684975fe9ce2f23ed83f91fe5d"))return 0;
    if(snprintf(path,sizeof path,"%s/Jun-T3-name.4bpp",root)>=(int)sizeof path)return 0;
    f=fopen(path,"rb");if(!f)return 0;
    ok=fread(name_pixels,1,sizeof name_pixels,f)==sizeof name_pixels && fgetc(f)==EOF;fclose(f);
    psx_sha256_compute((const uint8_t*)name_pixels,sizeof name_pixels,digest);
    for(unsigned i=0;i<32;i++)snprintf(hex+i*2,3,"%02x",digest[i]);
    if(!ok || strcmp(hex,"76d2af59e794ad6dc8b4eeaf78f39a0cc96b3636e08266208a72b67c692e5c81"))return 0;
    return 1;
}
static void initialize(void) {
    if(attempted)return;attempted=1;
    if(!load_ui()){fprintf(stderr,"Jun roster: private UI pack failed validation\n");return;}
    uint32_t allocation=psx_mod_alloc_guest_memory(0x40200,16);
    if(!allocation){free(ui);ui=NULL;fprintf(stderr,"Jun roster: guest allocation failed\n");return;}
    uint32_t area=(allocation+65535u)&~65535u;
    metadata=area;model_map=area+0x10000;model_sizes=area+0x20000;team_table=area+0x30000;ui_color=area+0x30100;
    uint32_t desc=area+0x30120;
    stock_icon_uv=psx_mod_read_word(0x8002152c+21*8);
    stock_icon_page=psx_mod_read_word(0x8002152c+21*8+4);
    const unsigned char *small=ui+ui_offsets[4]+544;
    for(unsigned y=0;y<58;y++)memcpy(loading_pixels+y*16,small+(y/2)*32,32);
    copy_guest(metadata,0x80097d40,92*4);
    copy_guest(model_map,0x800958c4,92);
    copy_guest(model_sizes,0x80095a9c,52*12);
    for(unsigned i=0;i<3;i++)copy_guest(model_sizes+(JUN_MODEL+i)*12,0x80095a9c+18*12,12);
    /* Body separation has its own eight-sphere table, independent of the
     * fourteen damage hurtboxes. The stock table ends at character 21;
     * indexing it with Jun's ID read 0x0000000e as a profile pointer. */
    body_profiles=model_sizes+0x1000;
    copy_guest(body_profiles,0x80096f60,22*4);
    psx_mod_write_word(body_profiles+23*4,psx_mod_read_word(0x80096f60+9*4));
    /* Native face animation indexes a separate four-byte table by model ID.
     * Its stock end aliases model-size data, so added IDs otherwise schedule
     * bogus MoveImage commands over faces and even the font atlas. Imported
     * Jun expressions are uploaded by tekken3_jun_face instead. */
    face_profiles=model_sizes+0x2000;
    copy_guest(face_profiles,0x800959cc,52*4);
    for(unsigned i=0;i<3;i++)psx_mod_write_word(face_profiles+(JUN_MODEL+i)*4,0xffffffff);
    /* Force indexes its boss-route pointers by character * 4 + costume.
     * Reserve a private extension; the native table is overlay-owned and
     * cannot be copied until that overlay is resident. */
    force_bosses=model_sizes+0x3000;
    static const unsigned jun_bosses[4]={7,4,9,13}; /* Xiaoyu, Yoshimitsu, Jin, Heihachi */
    for(unsigned i=0;i<4;i++) {
        psx_mod_write_half(force_bosses+0x200+i*4,jun_bosses[i]);
        psx_mod_write_half(force_bosses+0x202+i*4,0xffff); /* Native outfit selection. */
        psx_mod_write_word(force_bosses+(JUN_ID*4+i)*4,force_bosses+0x200);
    }
    copy_guest(desc,0x80022274,12);
    psx_mod_write_word(desc,desc+12);copy_host(desc+12,(const unsigned char*)"JUN",4);
    psx_mod_write_byte(desc+4,JUN_ID);psx_mod_write_byte(desc+9,JUN_ID);
    psx_mod_write_byte(desc+5,24);
    /* A distinct arena ID preserves stock Jin and Forest stages. Mode-owned
     * arenas (Ball/Force) retain their native overrides. Keep Jin's music. */
    psx_mod_write_byte(desc+10,tekken3_jun_stage_initialize());
    psx_mod_write_byte(desc+11,JUN_STAGE_MUSIC);
    cpu_profiles=model_sizes+0x5000;
    jun_cpu_initialize(cpu_profiles);
    /* Distinct native cache IDs prevent mixed-outfit mirrors sharing headers. */
    for(unsigned i=92;i<96;i++) {
        psx_mod_write_word(metadata+i*4,desc);
        psx_mod_write_byte(model_map+i,JUN_MODEL+(i==95?0:i-92));
    }
    /* A distinct image-cache ID avoids treating Jun as the blank portrait
     * (21) when changing between character select and the loading screen. */
    psx_mod_write_word(ui_color,0xead8b397);
    portrait_bank=model_sizes+0x4000;
    usage_mask=model_sizes+0x4100;
    static const unsigned order[22]={1,14,11,15,10,20,0,7,4,5,13,3,2,9,6,19,12,17,16,18,8,JUN_ID};
    for(unsigned i=0;i<24;i++) {
        psx_mod_write_half(team_table+i*6,41+(i%8)*36);
        psx_mod_write_half(team_table+i*6+2,67+(i/8)*63);
        psx_mod_write_half(team_table+i*6+4,i<22?order[i]*4:0x58);
    }
    initialized=1;
    fprintf(stderr,"Jun roster: registered character 23 / model 52; 22 selectable fighters; UI loaded\n");
}

static void patch_force_bosses(void) {
    /* BNS record 7, loaded at 800B0548: func_800B2658 dereferences
     * 800B6378[actor->selection] and then reads one {fighter, outfit}
     * pair for the current stage. The stock table has only 92 pointers;
     * Jun's 92..95 selections instead read the adjacent actor state at
     * 800B64E8. That can select Paul from zeroed memory or fault at
     * 800B26D4 when those actor words become invalid route pointers.
     * Match the loaded code before touching it, and rebuild the copied
     * table whenever the overlay restores its original instructions.
     * All stock routes and the neighbouring actor state stay untouched. */
    if(psx_mod_read_word(0x800b2658)!=0x27bdffb8 ||
       psx_mod_read_word(0x800b2694)!=0x3c05800b ||
       psx_mod_read_word(0x800b2698)!=0x24a56378 ||
       psx_mod_read_word(0x800b26d4)!=0x84720002)return;
    copy_guest(force_bosses,0x800b6378,92*4);
    patch(0x800b2694,0x3c05800b,0x3c050000|(force_bosses>>16));
    patch(0x800b2698,0x24a56378,0x34a50000|(force_bosses&65535));
    fprintf(stderr,"Jun roster: Tekken Force boss table extended; Jun route Xiaoyu / Yoshimitsu / Jin / Heihachi\n");
}
static void patch_tables(void) {
    tekken3_jun_stage_tick();
    jun_cpu_patch(cpu_profiles);
    patch_force_bosses();
    /* The memory-card format already saves 22 counter rows. Row 21 belongs
     * to non-selectable Force enemies and is unused for player statistics;
     * use it for Jun without extending the save or overwriting another row.
     * Keep her roster/model identity 23 everywhere outside statistics. */
    psx_mod_write_word(usage_mask,(psx_mod_read_word(0x80097ef0)&0x1fffff)|(1u<<21));
    if(psx_mod_read_word(0x800c19b8)==0x27bdff18 &&
       psx_mod_read_word(0x800c1a20)==0x3442ffff) {
        patch(0x800c1a1c,0x3c02001f,0x3c02003f); /* Include saved Jun row 21. */
        /* The descriptor getters are RAM-patched and therefore interpreted;
         * linker wrappers on them do not run. Route just the usage name
         * calls through a clean, wrapped native stub before the getter. */
        patch(0x800c1550,0x0c013bfc,0x0c014a52);
    }
    if(psx_mod_read_word(0x800e0860)==0x27bdfe60) {
        /* Other records retain the native roster; only Character Usage
         * substitutes saved row 21 for Jun's out-of-range roster bit 23. */
        patch(0x800e0864,0x3c03ffdf,0x3c03001f);
        patch(0x800e0a38,0x3c02800f,0x3c020000|(usage_mask>>16));
        patch(0x800e0a3c,0x8c53c44c,0x8c530000|(usage_mask&65535));
        patch(0x800dffc0,0x0c013bf2,0x0c014a52);
    }
    static const uint32_t face_refs[][2]={
        {0x80033d14,0x80033d20},{0x80034248,0x80034250},
        {0x8003435c,0x80034364},{0x800343e4,0x800343ec},
        {0x800344d8,0x800344e0}};
    for(unsigned i=0;i<sizeof face_refs/sizeof *face_refs;i++) {
        unsigned reg=i==4?2:3;
        patch(face_refs[i][0],0x3c008009|(reg<<16),0x3c000000|(reg<<16)|(face_profiles>>16));
        patch(face_refs[i][1],0x240059cc|(reg<<21)|(reg<<16),
              0x34000000|(reg<<21)|(reg<<16)|(face_profiles&65535));
    }
    patch(0x8003ec64,0x3c038009,0x3c030000|(body_profiles>>16));
    patch(0x8003ec68,0x24636f60,0x34630000|(body_profiles&65535));
    static const uint32_t descriptors[]={0x8004efd8,0x8004f008,0x8004f29c,0x8004f374,0x8004f478,0x8004f580,0x8004f5e4,0x8004f648,0x8004f70c};
    for(unsigned i=0;i<sizeof descriptors/sizeof *descriptors;i++)
        indirect(descriptors[i],descriptors[i]==0x8004f648?0x24427d40:0x24637d40);
    indirect(0x8003618c,0x244258c4);indirect(0x800361c4,0x246358c4);
    indirect(0x800361f8,0x244658c4);indirect(0x8003623c,0x246358c4);
    immediate(0x800361b0,0x5c,0x60);immediate(0x80036214,0x5c,0x60);immediate(0x80036228,0x5c,0x60);
    immediate(0x8002d1e8,21,24);
    indirect(0x800363a0,0x26315a9c);
    for(uint32_t a=0x8004efb0;a<0x8004f750;a+=4) {
        uint32_t w=psx_mod_read_word(a),op=w>>26;
        if((op==10 || op==11) && (w&65535)==0x5d)patch(a,w,(w&0xffff0000)|0x60);
        if((op==10 || op==11) && (w&65535)==0x16)patch(a,w,(w&0xffff0000)|0x18);
    }
    psx_mod_write_word(0x80097ef0,psx_mod_read_word(0x80097ef0)|(1u<<JUN_ID));
    psx_mod_write_word(0x80097ef4,psx_mod_read_word(0x80097ef4)|(1u<<JUN_ID));
    /* Every stock table reference is redirected; original IDs 21 and 22 and
     * their descriptor/model entries remain intact in the copied tables. */
    static const uint32_t positions[]={0x80052e24,0x800531b4,0x800532d0,0x800533a4,0x800534d0,0x800535d0,0x80053704,0x8005427c,0x80054414,0x8005449c,0x80054858,0x80054d10,0x80054e6c};
    for(unsigned i=0;i<sizeof positions/sizeof *positions;i++) {
        uint32_t w=psx_mod_read_word(positions[i]);
        if(w>>26==9 && (w&65535)==0x2768)indirect(positions[i],w);
    }
    static const uint32_t stride[]={0x80052e0c,0x8005428c,0x80054424,0x800544ac,0x80054840,0x80054d78,0x80054da8};
    for(unsigned i=0;i<sizeof stride/sizeof *stride;i++)patch(stride[i],stride[i]==0x80054840?0x00431023:0x00441023,0);
    static const uint32_t columns[]={0x800531ec,0x80053308,0x800533e8,0x8005350c,0x80053614,0x80053748};
    for(unsigned i=0;i<sizeof columns/sizeof *columns;i++)immediate(columns[i],7,8);
    immediate(0x80054ed4,21,22);
    /* Existing generated entry supplies a small host navigation helper.
     * RA distinguishes this call from real descriptor lookups. */
    patch(0x80053c08,0x3c02800b,0x0c014a4e);patch(0x80053c0c,0x2442df00,0);
    patch(0x8005387c,0x3c02800b,0x0c014a4e);patch(0x80053880,0x2442df00,0);
    patch(0x80052de4,0x27bdffe0,0x08014a50);patch(0x80052de8,0xafb10014,0);
    for(uint32_t a=0x80052de4;a<0x80054ee0;a+=4) {
        uint32_t w=psx_mod_read_word(a),op=w>>26;
        if((op==10 || op==11) && (w&65535)==0x58)patch(a,w,(w&0xffff0000)|0x60);
    }
}
static void icon_upload(unsigned index,unsigned x,unsigned y,unsigned palette_y) {
    const unsigned char *p=ui+ui_offsets[index];
    jun_ui_palette_upload(&selector_palette,palette_y,(const uint16_t*)(p+20));
    jun_ui_texture_upload(&selector_texture,x,y,(const uint16_t*)(p+544));
}
static void grey_upload(unsigned screen) {
    const unsigned char *colors=ui+ui_offsets[screen==11?4:2]+20;
    for(unsigned i=0;i<256;i++)grey_colors[i]=jun_ui_grey(u16(colors+i*2));
    jun_ui_palette_upload(&grey_palette,JUN_GREY_ROW,grey_colors);
    grey_screen=screen;
}
void tekken3_jun_roster_tick(void) {
    if(enabled<0){const char *p=getenv("TEKKEN3_JUN_ROSTER");enabled=!p || strcmp(p,"0");}
    if(!enabled)return;
    if(!initialized)initialize();if(!initialized)return;
    patch_tables();
    int cabinet=psx_mod_read_word(0x800ae204)==9 && psx_mod_read_word(0x8010ff4c)==0x27bdffd0;
    unsigned screen=psx_mod_read_word(0x800ae204);
    for(unsigned p=0;p<2;p++)
        tekken3_outfits_set_character_override(p,cabinet &&
            psx_mod_read_word(0x80118668+p*0x7c)==JUN_ID?JUN_ID:-1);
    /* The last selector packets can still be visible while screen 11 is
     * preparing its first frame. Retain their CLUT until gameplay starts. */
    if(screen==8 || (!cabinet && screen!=10 && screen!=11 && screen!=icon_screen)) {
        jun_ui_palette_release(&selector_palette,502);
        jun_ui_texture_release(&selector_texture,ICON_X,ICON_Y);
    }
    if(screen!=11) {
        jun_ui_palette_release(&loading_palette,503);
        jun_ui_texture_release(&loading_texture,LOADING_ICON_X,ICON_Y);
    }
    if(screen==8 || screen!=grey_screen)
        jun_ui_palette_release(&grey_palette,JUN_GREY_ROW);
    else if(grey_palette.active)grey_upload(screen);
    if(cabinet) {
        /* Extend the selector's archive directory, not its image payloads.
         * Rebase each relative offset onto the resident native archive.
         * Jun's decoder hook supplies the imported TIM for entry 23. */
        if(psx_mod_read_word(0x8010e49c)==0x3c02800c &&
           psx_mod_read_word(0x8010e4a4)==0x2455912c &&
           psx_mod_read_word(0x800b912c)==22) {
            psx_mod_write_word(portrait_bank,24);
            for(unsigned i=0;i<24;i++) {
                unsigned native=i<22?i:21;
                uint32_t record=0x800b912c+4+native*8;
                psx_mod_write_word(portrait_bank+4+i*8,
                    0x800b912c+psx_mod_read_word(record)-portrait_bank);
                psx_mod_write_word(portrait_bank+8+i*8,psx_mod_read_word(record+4));
            }
            patch(0x8010e49c,0x3c02800c,0x3c020000|(portrait_bank>>16));
            patch(0x8010e4a4,0x2455912c,0x34550000|(portrait_bank&65535));
        }
        for(unsigned p=0;p<2;p++) {
            uint32_t panel=0x80118628+0x24+p*0x7c;
            if(psx_mod_read_word(panel+0x14)==JUN_ID) {
                const unsigned char *portrait=ui+ui_offsets[0];
                unsigned clut=psx_mod_read_half(panel+0x5c);
                gr_vram_transfer_in(psx_mod_read_half(panel+0x58),
                    psx_mod_read_half(panel+0x5a),63,252,(const uint16_t*)(portrait+544));
                gr_vram_transfer_in((clut&63)*16,clut>>6,256,1,(const uint16_t*)(portrait+20));
            }
        }
        gr_vram_transfer_in(736,112,6,16,name_pixels);
        immediate(0x8010d5f0,0x1f,0x9f);
        immediate(0x8010d9b4,22,24);immediate(0x8010da30,22,24);
        immediate(0x8010db38,23,24);
        immediate(0x8010dc0c,22,24);immediate(0x8010f7b0,22,24);
        psx_mod_write_byte(0x800b9018+10,JUN_ID);
        if(psx_mod_read_half(0x800ae224)<=1 && psx_mod_read_word(0x80118648)>=21) {
            psx_mod_write_word(0x80118648,ROSTER_COUNT);
            psx_mod_write_word(0x80118644,psx_mod_read_word(0x80118644)|(1u<<JUN_ID));
            for(unsigned i=0;i<22;i++) {
                uint32_t n=0x801296c8+i*12;unsigned col=i%11,row=i/11;
                psx_mod_write_byte(n+1,row?col:22);psx_mod_write_byte(n+2,row?22:col+11);
                psx_mod_write_byte(n+3,row*11+(col+10)%11);psx_mod_write_byte(n+4,row*11+(col+1)%11);
                psx_mod_write_byte(n+5,1);psx_mod_write_half(n+8,3+33*col);psx_mod_write_half(n+10,row*62);
            }
            psx_mod_write_half(0x801296c8+10*12+6,JUN_ID);
        }
    }
    if(cabinet || screen==10 || (screen==11 && selector_palette.active) ||
       (screen==icon_screen && screen!=11 && screen!=8)) {
        icon_upload(2,ICON_X,ICON_Y,502);
    }
    if(screen==11 && loading_palette.active) {
        /* Arcade loading thumbnails have half-height pixels. The PS1's
         * framed team cards use 58 rows, so preserve their aspect ratio. */
        jun_ui_palette_upload(&loading_palette,503,(const uint16_t*)(ui+ui_offsets[4]+20));
        /* Do not overwrite the still-visible selector thumbnail with the
         * half-height loading art; the two images use different texels. */
        jun_ui_texture_upload(&loading_texture,LOADING_ICON_X,ICON_Y,loading_pixels);
    }
    /* Selection identity, including the native actor, stays 23. */
    if(psx_mod_read_word(0x800ae204)==8) {
        static int selected=-1;int wanted=0;
        for(unsigned p=0;p<2;p++)if(psx_mod_read_half(0x800a9240+p*0x188c)==JUN_ID) {
            wanted=1;gr_vram_transfer_in(464,p*256,6,16,name_pixels);
        }
        if(wanted!=selected){tekken3_jun_select(wanted);selected=wanted;}
    }
}

void __wrap_func_80052938(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->gpr[31]==0x80053c10 || cpu->gpr[31]==0x80053884)) {
        int primary=cpu->gpr[31]==0x80053884;
        unsigned b=psx_mod_read_half(0x800adf00+cpu->gpr[primary?19:20]*2);
        unsigned state=cpu->gpr[16];int x=psx_mod_read_word(state+8),y=psx_mod_read_word(state+12);
        if(y<0 || y>2)y=0;if(x<0 || x>=(y==2?6:8))x=0;
        int dx=((b>>13)&1)-((b>>15)&1),dy=((b>>14)&1)-((b>>12)&1);
        if(dx){int n=y==2?6:8;x=(x+dx+n)%n;}
        else {y+=dy;if(y<0)y=0;if(y>2)y=2;if(y==2 && x>5)x=5;}
        cpu->gpr[17]=x;cpu->gpr[primary?18:19]=y;cpu->pc=primary?0x80053910:0x80053c9c;return;
    }
    __real_func_80052938(cpu);
}
void __wrap_func_80052940(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->gpr[31]==0x80053a1c || cpu->gpr[31]==0x80053d90)) {
        uint32_t root=cpu->gpr[4],state=cpu->gpr[5],input=cpu->gpr[6];
        unsigned x=psx_mod_read_word(state+8),y=psx_mod_read_word(state+12),n=psx_mod_read_word(state+44);
        cpu->gpr[29]-=32;psx_mod_write_word(cpu->gpr[29]+20,cpu->gpr[17]);
        if(psx_mod_read_word(root)==2 && x==5 && y==2 && (input&0xf0) && n<8 &&
           (psx_mod_read_word(state+36)&(1u<<JUN_ID))) {
            /* Append the extra roster entry to the real native team array;
             * continue through the game's availability, sound and completion
             * code with the same saved-register layout as its prologue. */
            psx_mod_write_word(cpu->gpr[29]+16,cpu->gpr[16]);
            psx_mod_write_word(cpu->gpr[29]+24,cpu->gpr[18]);
            psx_mod_write_word(cpu->gpr[29]+28,cpu->gpr[31]);
            cpu->gpr[17]=root;cpu->gpr[16]=state;cpu->gpr[18]=n;
            /* Team Battle reserves Start for random teams; Triangle selects
             * the third costume, as on native three-costume fighters. */
            cpu->gpr[6]=JUN_ID*4+((input&0x10)?2:!!(input&0x60));
            psx_mod_write_word(state+56+n*4,cpu->gpr[6]);
            cpu->pc=0x80052f98;return;
        }
        cpu->pc=0x80052dec;return;
    }
    __real_func_80052940(cpu);
}
void __wrap_func_8004B790(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x8004b790) && cpu->gpr[4]==JUN_ID) {
        cpu->gpr[2]=ui_color;cpu->pc=cpu->gpr[31];return;
    }
    __real_func_8004B790(cpu);
}
void __wrap_func_8004B928(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x8004b928)) {
        uint32_t slot=cpu->gpr[29]+16;
        unsigned id=psx_mod_read_word(slot)>>2;
        /* Usage rows use saved counter ID 21; all other Crow/empty callers
         * retain their native identity and art. */
        if(psx_mod_read_word(0x800ae204)!=8 &&
           (id==JUN_ID || (id==21 && cpu->gpr[31]==0x800c1538))) {
            icon_screen=psx_mod_read_word(0x800ae204);
            if(icon_screen!=11)icon_upload(2,ICON_X,ICON_Y,502);
            else {
                jun_ui_palette_upload(&loading_palette,503,(const uint16_t*)(ui+ui_offsets[4]+20));
                jun_ui_texture_upload(&loading_texture,LOADING_ICON_X,ICON_Y,loading_pixels);
            }
            unsigned flags=psx_mod_read_word(slot+4),knocked_out=!!(flags&0x20);
            if(knocked_out) {
                /* Native KO replaces the CLUT with 0x7d50, whose indices
                 * belong to stock portraits. Jun needs her own grey CLUT.
                 * Leave all geometry/other flags intact. */
                grey_upload(icon_screen);
                psx_mod_write_word(slot+4,flags&~0x20u);
            }
            psx_mod_write_word(slot,21*4);
            psx_mod_write_word(0x8002152c+21*8,jun_ui_icon_uv(icon_screen==11,knocked_out));
            psx_mod_write_half(0x8002152c+21*8+4,ICON_PAGE);
        } else if(id==21) {
            psx_mod_write_word(0x8002152c+21*8,stock_icon_uv);
            psx_mod_write_word(0x8002152c+21*8+4,stock_icon_page);
        }
    }
    __real_func_8004B928(cpu);
}
static void usage_arguments(CPUState *cpu,int two_players) {
    /* The three write routines enter generated code just after MULT, not
     * at their native entrypoints. Update its already-computed product too,
     * so the following division-by-22 sequence uses the saved Jun row. */
    if(cpu->gpr[4]==JUN_ID) {
        uint64_t product=(uint64_t)21*0x2e8ba2e9u;
        cpu->gpr[4]=21;cpu->hi=(uint32_t)(product>>32);cpu->lo=(uint32_t)product;
    }
    if(two_players && cpu->gpr[5]==JUN_ID)cpu->gpr[5]=21;
}
void __wrap_func_800513C0(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x800513c0))usage_arguments(cpu,0);
    __real_func_800513C0(cpu);
}
void __wrap_func_80051464(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80051464))usage_arguments(cpu,1);
    __real_func_80051464(cpu);
}
void __wrap_func_8005155C(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x8005155c))usage_arguments(cpu,1);
    __real_func_8005155C(cpu);
}
void __wrap_func_80051660(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80051660) && cpu->gpr[4]==JUN_ID)cpu->gpr[4]=21;
    __real_func_80051660(cpu);
}
void __wrap_func_80052948(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80052948)) {
        if(cpu->gpr[31]==0x800c1558) {
            if(cpu->gpr[4]==21)cpu->gpr[4]=JUN_ID;
            cpu->pc=0x8004eff0;return;
        }
        if(cpu->gpr[31]==0x800dffc8) {
            if(cpu->gpr[4]==21*4)cpu->gpr[4]=JUN_ID*4;
            cpu->pc=0x8004efc8;return;
        }
    }
    __real_func_80052948(cpu);
}
void __wrap_func_80031BFC(CPUState *cpu) {
    if(tekken3_anna_portrait_decode(cpu))return;
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80031bfc) &&
       ((cpu->gpr[31]==0x8010e574 && psx_mod_read_word(cpu->gpr[16]+0x1c)==JUN_ID) ||
        (cpu->gpr[31]==0x8004c814 && cpu->gpr[20]<2 &&
         psx_mod_read_half(0x800add5c+cpu->gpr[20]*2)==JUN_ID))) {
        copy_host(cpu->gpr[5],ui+ui_offsets[0],ui_lengths[0]);
        cpu->gpr[2]=ui_lengths[0];cpu->pc=cpu->gpr[31];return;
    }
    __real_func_80031BFC(cpu);
}
/* Loading-screen portrait is the same native banded TIM. */
void __wrap_func_80052AD0(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && tekken3_jun_stage_load(cpu))return;
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80052ad0) &&
       cpu->gpr[31]==0x80052770 && cpu->gpr[20]<2 &&
       psx_mod_read_half(0x800add5c+cpu->gpr[20]*2)==JUN_ID) {
        /* The loader expects compressed input. Its decoder wrapper supplies
         * the validated TIM; never feed a raw TIM into the native LZ decoder. */
        psx_mod_write_byte(cpu->gpr[4],0);
        cpu->gpr[2]=0;cpu->pc=cpu->gpr[31];return;
    }
    __real_func_80052AD0(cpu);
}
void __wrap_func_80052958(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80052958) && cpu->gpr[5]==JUN_ID)cpu->gpr[5]=9;
    __real_func_80052958(cpu);
}
void __wrap_func_80052990(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80052990) && cpu->gpr[5]==JUN_ID)cpu->gpr[5]=9;
    __real_func_80052990(cpu);
}
void __wrap_func_8006BF20(CPUState *cpu) {
    /*
     * These are BNS asset requests, not voice/event IDs. The native actor
     * loader requests four records per model (95 + model * 4). Jun's
     * models 52..54 have no disc records, so each costume needs Jin's
     * model-18 envelope before the imported model and moves are installed.
     * This must also run during loading and Tekken Force transitions.
     */
    const uint32_t first=95+JUN_MODEL*4;
    if(tekken3_jun_roster_enabled() &&
       (cpu->pc==0 || cpu->pc==0x8006bf20) &&
       cpu->gpr[4]>=first && cpu->gpr[4]<first+3*4)
        cpu->gpr[4]=95+18*4+(cpu->gpr[4]-first)%4;
    __real_func_8006BF20(cpu);
}
void __wrap_func_8003626C(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x8003626c) && cpu->gpr[4]>=JUN_MODEL && cpu->gpr[4]<JUN_MODEL+3)cpu->gpr[4]=18;
    __real_func_8003626C(cpu);
}
void __wrap_func_80036294(CPUState *cpu) {
    unsigned model=psx_mod_read_half(cpu->gpr[4]+28);
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x80036294) && model>=JUN_MODEL && model<JUN_MODEL+3) {
        cpu->gpr[2]=psx_mod_read_byte(0x80095950+18);cpu->pc=cpu->gpr[31];return;
    }
    __real_func_80036294(cpu);
}
void __wrap_func_800362C4(CPUState *cpu) {
    unsigned model=psx_mod_read_half(cpu->gpr[4]+28);
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x800362c4) && model>=JUN_MODEL && model<JUN_MODEL+3) {
        cpu->gpr[2]=psx_mod_read_byte(0x80095984+18);cpu->pc=cpu->gpr[31];return;
    }
    __real_func_800362C4(cpu);
}
void __wrap_func_8003F044(CPUState *cpu) {
    if(tekken3_jun_roster_enabled() && (cpu->pc==0 || cpu->pc==0x8003f044) &&
       psx_mod_read_half(cpu->gpr[4]+24)==JUN_ID) {
        /* TTT1's Jun radius profile (80194C20[28] -> 800112DC) is byte-for-
         * byte identical to SLUS-00402's standard human profile. The stock
         * lookup has only 22 entries and ID 23 otherwise reads a null pointer. */
        uint32_t profile=psx_mod_read_word(0x80096ff0+9*4);
        for(unsigned i=0;i<14;i++) {
            unsigned radius=psx_mod_read_half(profile+i*2);
            psx_mod_write_half(cpu->gpr[4]+0x218+i*20,radius);
            psx_mod_write_word(cpu->gpr[4]+0x21c+i*20,radius*radius);
        }
        cpu->pc=cpu->gpr[31];return;
    }
    __real_func_8003F044(cpu);
}

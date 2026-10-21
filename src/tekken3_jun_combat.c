/* Source-derived solo combat adapter. See combat-report.json for coverage. */
#include "psx_runtime.h"
#include "mod_plugins.h"
#include "tekken3_jun_pack.h"
#include "tekken3_jun_assets.h"
#include "tekken3_fight_camera.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern unsigned tekken3_jun_motion_mode(void);
extern unsigned tekken3_jun_player_motion_mode(unsigned player);
extern int tekken3_jun_roster_enabled(void);
extern void tekken3_jun_face(unsigned player,unsigned variant);
extern void __real_func_8002D178(CPUState *cpu);
extern void __real_func_80038B4C(CPUState *cpu);
extern void __real_func_800389C0(CPUState *cpu);
extern void __real_func_8002CC28(CPUState *cpu);
extern void __real_func_8002CD7C(CPUState *cpu);
extern void __real_func_80059890(CPUState *cpu);
extern void __real_func_8006A3BC(CPUState *cpu);
extern void __real_func_8002D264(CPUState *cpu);
extern void __real_func_8002E8D0(CPUState *cpu);
extern void __real_func_8002E0BC(CPUState *cpu);
extern void func_8002CA84(CPUState *cpu);
static uint32_t guest,size,count,records,neutral;
static unsigned char *data;
static int attempted,loaded;
typedef struct {
    uint32_t native_base,native_common,alias_table,original_alias,header,records,source,hit_bones;
} PlayerCombat;
static PlayerCombat players[2];
static uint32_t clip_addresses[1024],clip_offsets[1024];
static uint32_t patterns[1024];
static unsigned pattern_count;
static uint16_t native_aliases[4023];
/* Imported recovery IDs -> the receiving fighter's native engine aliases.
 * Zero means no equivalent: unique paired victim clips must stay imported. */
static uint16_t recovery_aliases[1024];
static unsigned char native_reactions[4023];
static uint32_t source_aliases[5515];
typedef struct {uint16_t source,native;unsigned count;uint32_t clips[128];} ContactGroup;
static ContactGroup groups[64];
static unsigned group_count;
static struct {unsigned record,mask,alternate,normal;} dynamic_hits[64];
static unsigned dynamic_count;
static uint32_t push_table=0x8001075c;
uint32_t tekken3_jun_push_base(void) {return push_table;}
static uint32_t word(const unsigned char *p) {
    return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static int source_record(uint32_t record) {
    for(unsigned p=0;p<2;p++)if(players[p].records && record>=players[p].records &&
       record<players[p].records+count*56 && (record-players[p].records)%56==0)return 1;
    return 0;
}
int tekken3_jun_source_condition(uint32_t actor,unsigned kind) {
    /* Contact conditions 69..75 remain in the separate contact pass. */
    return kind>=76 && kind<=82 && source_record(psx_mod_read_word(actor+0x54));
}
int tekken3_jun_source_transition(CPUState *cpu) {
    uint32_t actor=cpu->gpr[17];unsigned kind=cpu->gpr[3];
    if(kind<45 || kind>47 || !source_record(psx_mod_read_word(actor+0x1a4)))return 0;
    /* TTT 80100E24..80100EF4, called only after the native transition's
     * frame gate has committed. s2 retains the native root-refresh decision. */
    psx_mod_write_half(actor+0x58,1);psx_mod_write_half(actor+0x50,1);
    psx_mod_write_half(actor+0x74,0);
    psx_mod_write_word(actor+0x4c,psx_mod_read_word(actor+0x1a4));
    psx_mod_write_byte(actor+0xb9,kind==45?8:kind-34);
    if(kind==45)psx_mod_write_half(actor+0x2c,psx_mod_read_half(actor+0x2a));
    psx_mod_write_half(actor+0xe,psx_mod_read_half(actor+(kind==45?0x2a:0x34)));
    if(kind==45 || cpu->gpr[18]) {
        psx_mod_write_word(actor,psx_mod_read_word(actor+0xf68));
        psx_mod_write_word(actor+8,psx_mod_read_word(actor+0xf70));
    }
    return 1;
}
int tekken3_jun_source_rotation(uint32_t actor) {
    unsigned mode=psx_mod_read_byte(actor+0xb9);
    if((mode!=12 && mode!=13) || !source_record(psx_mod_read_word(actor+0x54)))return 0;
    /* The PS1 camera uses 65536 angle units; TTT uses 4096. Match the
     * source camera-plane axis, closest half-turn, and eight-frame blend. */
    int yaw=tekken3_fight_camera_yaw()%65536;
    int axis=(0x4000-yaw)%65535;
    if(psx_mod_read_half(actor+0x12))axis+=0x8000;
    if(mode==13)axis=(int16_t)axis-0x4000;
    int facing=psx_mod_read_half(actor+0x2c);
    int delta=(int16_t)(facing-axis);
    unsigned distance=(uint16_t)(delta<0?65535-delta:delta);
    if(distance>=0x4000)axis+=0x8000;
    int frame=(int16_t)psx_mod_read_half(actor+0x5c);if(frame>8)frame=8;
    int step=(int16_t)(((int16_t)(axis-facing)*frame)/8);
    if(step>0x71c)step=0x71c;if(step< -0x71c)step= -0x71c;
    psx_mod_write_half(actor+0x2c,(uint16_t)(facing+step));
    psx_mod_write_half(actor+0xe,(uint16_t)(facing+step));
    return 1;
}
void __wrap_func_8002E0BC(CPUState *cpu) {
    if(cpu->pc==0 || cpu->pc==0x8002e0bc) {
        unsigned kind=psx_mod_read_byte(cpu->gpr[4]+3),actor=cpu->gpr[5],match=0;
        if(kind>=76 && kind<=82 && source_record(psx_mod_read_word(actor+0x54))) {
            int relative=(int16_t)psx_mod_read_half(actor+0x2e);
            if(kind==76)match=(int16_t)psx_mod_read_half(actor+0x30)<=0x4000;
            else if(kind==77)match=relative<0;
            else if(kind==78)match=relative>=0;
            else {
                int axis=0x4000-tekken3_fight_camera_yaw()%65536;
                unsigned quarter=(uint16_t)(psx_mod_read_half(actor+0x2c)-axis+0x2000)/0x4000;
                static const unsigned wanted[4]={1,2,0,3};
                match=quarter==wanted[kind-79];
            }
            cpu->gpr[2]=match;cpu->pc=cpu->gpr[31];return;
        }
    }
    __real_func_8002E0BC(cpu);
}
static void patch_base(uint32_t high_at,uint32_t low_at,unsigned reg,uint32_t target) {
    psx_mod_write_code_word(high_at,0x3c000000u|(reg<<16)|((target+0x8000)>>16));
    psx_mod_write_code_word(low_at,0x24000000u|(reg<<21)|(reg<<16)|(target&65535));
}
static int load_tables(const char *root) {
    char path[4096];snprintf(path,sizeof path,"%s/Jun-TTT1-tables.jst",root);
    FILE *f=fopen(path,"rb");if(!f)return 0;
    unsigned char h[32];if(fread(h,1,32,f)!=32){fclose(f);return 0;}
    uint32_t bytes=word(h+8),nr=word(h+12),np=word(h+16),nc=word(h+20);
    uint32_t fixed=nr*42+np+nc*4;
    if(word(h)!=0x3154534a || word(h+4)!=2 || nr<633 || nr>4096 ||
       np<1420 || np>65534 || (np&1) || nc<269 || nc>4096 ||
       bytes<32+fixed || bytes>1024*1024 || word(h+24) || word(h+28)){fclose(f);return 0;}
    unsigned char *p=malloc(bytes-32);if(!p){fclose(f);return 0;}
    int ok=fread(p,1,bytes-32,f)==bytes-32 && fgetc(f)==EOF;fclose(f);
    if(!ok){free(p);return 0;}
    unsigned chunks=0,event_offset=0,event_bytes=0;
    for(unsigned at=fixed;ok && at<bytes-32;) {
        if(bytes-32-at<8){ok=0;break;}
        unsigned type=word(p+at),n=word(p+at+4);at+=8;
        if(n>bytes-32-at){ok=0;break;}
        if(type==0x41494c41 && !(chunks&1) && n%4==0) {
            chunks|=1;
            for(unsigned i=0;i<n;i+=4) {
                unsigned a=jun_pack_half(p+at+i),b=jun_pack_half(p+at+i+2);
                if(a>=4023 || native_aliases[a] || !jun_pack_target(b,count)){ok=0;break;}
                native_aliases[a]=b;
            }
        } else if(type==0x41435253 && !(chunks&2) && n==sizeof source_aliases) {
            chunks|=2;for(unsigned i=0;i<5515;i++)source_aliases[i]=word(p+at+i*4);
        } else if(type==0x50555247 && !(chunks&4)) {
            chunks|=4;
            for(unsigned i=0;i<n;) {
                if(n-i<8 || group_count>=64){ok=0;break;}
                ContactGroup *g=&groups[group_count++];
                g->source=jun_pack_half(p+at+i);g->native=jun_pack_half(p+at+i+2);
                g->count=word(p+at+i+4);i+=8;
                if(g->count>128 || g->count*4>n-i || g->native>=52){ok=0;break;}
                for(unsigned k=0;k<g->count;k++)g->clips[k]=word(p+at+i+k*4);
                i+=g->count*4;
            }
        } else if(type==0x544e5645 && !(chunks&8)) {
            chunks|=8;event_offset=at;event_bytes=n;
            for(unsigned i=0;i<n;) {
                if(n-i<8){ok=0;break;}
                unsigned id=word(p+at+i),ne=word(p+at+i+4);i+=8;
                if(id<1024 || id>=4096 || !ne || ne>256 || ne*4>n-i || word(p+at+i+(ne-1)*4)){ok=0;break;}
                unsigned prev=0;
                for(unsigned k=0;k+1<ne;k++) {
                    unsigned v=word(p+at+i+k*4),frame=v&4095;
                    if(!frame || frame<prev || ((v>>12)&15)>3)ok=0;prev=frame;
                }
                i+=ne*4;
            }
        } else if(type==0x484e5944 && !(chunks&16) && n%16==0 && n/16<=64) {
            chunks|=16;dynamic_count=n/16;
            for(unsigned i=0;i<dynamic_count;i++) {
                dynamic_hits[i].record=word(p+at+i*16);
                dynamic_hits[i].mask=word(p+at+i*16+4);
                dynamic_hits[i].alternate=word(p+at+i*16+8);
                dynamic_hits[i].normal=word(p+at+i*16+12);
                if(dynamic_hits[i].record>=count || dynamic_hits[i].alternate>=nr || dynamic_hits[i].normal>=nr)ok=0;
            }
        } else ok=0;
        at+=n;
    }
    if(chunks!=31)ok=0;
    for(unsigned i=633;ok && i<nr;i++) {
        for(unsigned k=0;k<14;k++)if(!jun_pack_target(jun_pack_half(p+i*42+k*2),count))ok=0;
        for(unsigned k=15;k<21;k+=2)if(jun_pack_half(p+i*42+k*2)*2+20>np)ok=0;
        if(jun_pack_half(p+i*42+40)*2+20>np)ok=0;
    }
    uint32_t base=ok?psx_mod_alloc_guest_memory(fixed,16):0;
    if(!base){free(p);return 0;}
    /* Reaction destinations are semantic engine entries, even when their
     * records are stored in a character's bank. Removing all Jin-bank
     * records also removed these hit states and silently substituted idle.
     * Preserve the original 633 rows and the separate paired-reaction list. */
    for(unsigned i=0;i<633;i++)for(unsigned k=0;k<14;k++) {
        unsigned alias=jun_pack_half(p+i*42+k*2);
        if(alias<4023)native_reactions[alias]=1;
    }
    for(uint32_t at=0x800174c4;at<0x800177dc;at+=2) {
        unsigned alias=psx_mod_read_half(at);
        if(alias<4023)native_reactions[alias]=1;
    }
    for(unsigned i=0;i<4023;i++)if(native_aliases[i]>=8192) {
        unsigned index=native_aliases[i]-8192;
        /* Store alias + 1 so native alias zero is not the missing marker.
         * ALIA is ordered; retain the first equivalent engine entry. */
        if(!recovery_aliases[index])recovery_aliases[index]=(uint16_t)(i+1);
    }
    for(unsigned i=0;i<fixed;i++)psx_mod_write_byte(base+i,p[i]);
    uint32_t events=psx_mod_alloc_guest_memory(4096*4+4+event_bytes,16);
    if(!events){free(p);return 0;}
    uint32_t cursor=events+4096*4;
    psx_mod_write_word(cursor,0);
    for(unsigned i=0;i<4096;i++)psx_mod_write_word(events+i*4,
        i<470?psx_mod_read_word(0x800971f8+i*4):cursor);
    cursor+=4;
    for(unsigned i=0;i<event_bytes;) {
        unsigned id=word(p+event_offset+i),ne=word(p+event_offset+i+4);i+=8;
        psx_mod_write_word(events+id*4,cursor);
        for(unsigned k=0;k<ne;k++)psx_mod_write_word(cursor+k*4,word(p+event_offset+i+k*4));
        cursor+=ne*4;i+=ne*4;
    }
    free(p);
    patch_base(0x80041400,0x80041404,2,events);
    uint32_t push=base+nr*42,counter=push+np;
    patch_base(0x8002d7ac,0x8002d7b4,2,base);
    patch_base(0x80044590,0x80044598,2,base);
    patch_base(0x80044608,0x80044610,3,base);
    patch_base(0x80044664,0x8004466c,2,base);
    patch_base(0x800445c4,0x800445cc,2,counter);
    patch_base(0x80044ac0,0x80044ac4,3,counter);
    push_table=push;
    fprintf(stderr,"Jun combat: installed %u source reaction rows and original pushback data\n",nr-633);
    return 1;
}
static int load_combat(void) {
    if(attempted)return loaded;attempted=1;
    const char *root=tekken3_jun_asset_root();if(!root)return 0;
    char path[4096];snprintf(path,sizeof path,"%s/Jun-TTT1-combat.jmv",root);
    FILE *f=fopen(path,"rb");if(!f)return 0;
    unsigned char header[32];
    if(fread(header,1,32,f)!=32 || word(header)!=0x314d554a || word(header+4)!=4){fclose(f);return 0;}
    size=word(header+8);count=word(header+12);neutral=word(header+16);records=word(header+28);
    uint32_t ro=word(header+20),rn=word(header+24);
    if(size>16*1024*1024 || count>1024 || !count || neutral>=count || records!=32+count*16 || records+count*56>size || ro>size || rn>(size-ro)/4){fclose(f);return 0;}
    data=(unsigned char*)malloc(size);if(!data){fclose(f);return 0;}
    memcpy(data,header,32);
    int ok=fread(data+32,1,size-32,f)==size-32 && fgetc(f)==EOF;fclose(f);
    for(unsigned i=0;ok && i<rn;i++) {
        uint32_t r=word(data+ro+i*4);
        if(r>size-4 || (r&3) || word(data+r)>=size)ok=0;
    }
    if(!ok || !jun_pack_validate(data,size)){
        fprintf(stderr,"Jun combat: rejected invalid combat pack\n");
        free(data);data=NULL;return 0;
    }
    /* The guest arena is 1 MiB. Keep decoded motion in host memory; guest
     * records point at compact clip headers consumed by the decoder bridge. */
    uint32_t compact=records+count*56;
    for(unsigned i=0;i<count;i++) {
        uint32_t n=word(data+32+i*16+12);
        if(n>4096){free(data);data=NULL;return 0;}
        uint32_t rp=records+i*56;
        compact+=8+n*12+8;
        unsigned props=word(data+rp+32),j=0;
        do {compact+=4;} while(jun_pack_half(data+props+j++*4));
    }
    guest=psx_mod_alloc_guest_memory(compact,16);
    if(!guest){fprintf(stderr,"Jun combat: cannot allocate %u guest bytes\n",compact);return 0;}
    uint32_t cursor=records+count*56;
    for(unsigned i=0;i<cursor;i++)psx_mod_write_byte(guest+i,data[i]);
    for(unsigned i=0;i<count;i++) {
        uint32_t rp=records+i*56,cp=word(data+rp+12),n=word(data+32+i*16+12)*12;
        uint32_t clip=word(data+rp);
        if(cp>size || n>size-cp || clip>size-8)return 0;
        clip_addresses[i]=guest+cursor;clip_offsets[i]=clip;
        for(unsigned j=0;j<8;j++)psx_mod_write_byte(guest+cursor+j,data[clip+j]);
        psx_mod_write_word(guest+rp,guest+cursor);cursor+=8;
        psx_mod_write_word(guest+rp+12,guest+cursor);
        for(unsigned j=0;j<n;j++)psx_mod_write_byte(guest+cursor+j,data[cp+j]);
        cursor+=n;
        uint32_t sounds=word(data+rp+28),props=word(data+rp+32);
        psx_mod_write_word(guest+rp+28,guest+cursor);
        for(unsigned j=0;j<8;j++)psx_mod_write_byte(guest+cursor+j,j<6?data[sounds+j]:255);
        cursor+=8;
        psx_mod_write_word(guest+rp+32,guest+cursor);
        unsigned j=0;
        do {for(unsigned k=0;k<4;k++)psx_mod_write_byte(guest+cursor+k,data[props+j*4+k]);cursor+=4;}
        while(jun_pack_half(data+props+j++*4));
    }
    uint32_t po=ro+rn*4;
    if(po>size-4)return 0;
    pattern_count=word(data+po);po+=4;if(pattern_count>1024)return 0;
    for(unsigned i=0;i<pattern_count;i++) {
        if(po>size-4)return 0;
        unsigned command=data[po]|(unsigned)data[po+1]<<8,n=data[po+2]|(unsigned)data[po+3]<<8;po+=4;
        if(command!=0xe000+i || n<3 || n>65 || n*2>size-po)return 0;
        patterns[i]=psx_mod_alloc_guest_memory(n*2,4);if(!patterns[i])return 0;
        for(unsigned j=0;j<n*2;j++)psx_mod_write_byte(patterns[i]+j,data[po+j]);po+=n*2;
    }
    if(!load_tables(root))return 0;
    fprintf(stderr,"Jun combat: loaded %u source records and %u input sequences at %08X\n",count,pattern_count,guest);
    loaded=1;
    return 1;
}
static void keep_native_reactions(uint32_t aliases,uint32_t missing,unsigned char keep[4023]) {
    uint16_t pending[4023];unsigned head=0,tail=0;
    memcpy(keep,native_reactions,4023);
    for(unsigned i=0;i<4023;i++)if(keep[i])pending[tail++]=(uint16_t)i;
    while(head<tail) {
        unsigned alias=pending[head++];
        /* Jun's translated common locomotion already handles this entry.
         * Do not follow the donor's neutral/crouch graph into Jin attacks. */
        if(native_aliases[alias])continue;
        uint32_t record=psx_mod_read_word(aliases+alias*4);
        if(record==missing || record<0x80010000 || record>0x801fffc8)continue;
        unsigned next=psx_mod_read_half(record+16);
        if(next<4023 && !keep[next]){keep[next]=1;pending[tail++]=(uint16_t)next;}
        /* Terminal cancel destinations can differ from record + 16. Keep
         * their native recovery chains too (e.g. A46 -> A47), but never
         * promote ordinary input-command links to donor attacks. */
        uint32_t cancel=psx_mod_read_word(record+12);
        for(unsigned i=0;i<1024 && cancel>=0x80010000 && cancel<=0x801ffff4;i++,cancel+=12) {
            unsigned command=psx_mod_read_half(cancel);
            if(command==0xc00d)break; /* End of a shared cancel subroutine. */
            if(command!=0xc000)continue;
            next=psx_mod_read_half(cancel+6);
            if(next<4023 && !keep[next]){keep[next]=1;pending[tail++]=(uint16_t)next;}
            break;
        }
    }
}
static void restore_legacy_jump_velocity(PlayerCombat *p,uint32_t source) {
    /* Older v4 exports wrote only damage into word +14, discarding its
     * signed movement halfword at +16. Native 8003F3E8 reads that velocity
     * during the jump's +19..+1A frame window. Direction/animation alone do
     * not move the fighter. Repair only semantic jump entries in old packs;
     * corrected exports retain their original arcade velocities unchanged.
     * Use the loaded native jump profile for compatibility, not an invented
     * speed or a replacement animation. Native alias 82 may be absent, so
     * its forward variant falls back to 81 (backward variants to 83). */
    for(unsigned alias=0x7f;alias<=0x88;alias++) {
        unsigned imported=native_aliases[alias];
        if(imported<8192 || imported>=8192+count)continue;
        uint32_t record=p->records+(imported-8192)*56;
        unsigned direction=(psx_mod_read_word(record+4)>>16)&3;
        if((direction!=1 && direction!=2) || psx_mod_read_half(record+22) ||
           !psx_mod_read_byte(record+25))continue;
        uint32_t native=psx_mod_read_word(p->original_alias+alias*4);
        int valid=native>=0x80010000 && native<=0x801fffc8 && native!=source-56;
        if(!valid || !psx_mod_read_half(native+22))
            native=psx_mod_read_word(p->original_alias+(direction==1?0x81:0x83)*4);
        if(native>=0x80010000 && native<=0x801fffc8 && native!=source-56)
            psx_mod_write_half(record+22,psx_mod_read_half(native+22));
    }
}
static int ready(unsigned player) {
    if(tekken3_jun_player_motion_mode(player)!=2 || !load_combat())return 0;
    PlayerCombat *p=&players[player];
    uint32_t slot=0x800adc20+player*4,base=psx_mod_read_word(slot);
    if(base==p->header)base=p->native_base;
    if(base<0x80010000 || base>0x801f0000 || (psx_mod_read_word(base)&0xffff)!=0x0901)return 0;
    uint32_t common=psx_mod_read_word(0x800adc28);
    if(base!=p->native_base || psx_mod_read_word(slot)!=p->header || common!=p->native_common ||
       psx_mod_read_word(base+8)!=p->source || psx_mod_read_word(base+12)!=p->original_alias) {
        uint32_t source=psx_mod_read_word(base+8);
        p->original_alias=psx_mod_read_word(base+12);
        if(!p->alias_table)p->alias_table=psx_mod_alloc_guest_memory((8192+count)*4,16);
        if(!p->header)p->header=psx_mod_alloc_guest_memory(64,16);
        if(!p->records)p->records=psx_mod_alloc_guest_memory(count*56,16);
        if(!p->hit_bones)p->hit_bones=psx_mod_alloc_guest_memory(count*8,16);
        if(!p->alias_table || !p->header || !p->records || !p->hit_bones)return 0;
        for(unsigned i=0;i<64;i+=4)psx_mod_write_word(p->header+i,psx_mod_read_word(base+i));
        uint32_t idle=p->records+neutral*56;
        unsigned native_count=psx_mod_read_word(base)>>16;
        unsigned char keep[4023];
        keep_native_reactions(p->original_alias,source-56,keep);
        for(unsigned i=0;i<8192+count;i++)psx_mod_write_word(p->alias_table+i*4,idle);
        for(unsigned i=0;i<4023;i++) {
            uint32_t original=psx_mod_read_word(p->original_alias+i*4);
            /* Keep actual hit/victim states, including character-owned
             * records and terminal continuations. Only donor attacks are
             * excluded; shared engine records remain available as before. */
            if(original>=source && original<source+native_count*56 && !keep[i])continue;
            if(original==source-56)continue; /* native missing-alias record */
            psx_mod_write_word(p->alias_table+i*4,original);
        }
        for(unsigned i=0;i<count;i++) {
            uint32_t dst=p->records+i*56;
            for(unsigned j=0;j<56;j+=4)psx_mod_write_word(dst+j,psx_mod_read_word(guest+records+i*56+j));
            psx_mod_write_word(p->hit_bones+i*8,word(data+records+i*56+40));
            psx_mod_write_word(p->hit_bones+i*8+4,0);
            psx_mod_write_word(dst+40,p->hit_bones+i*8);
            psx_mod_write_word(p->alias_table+(8192+i)*4,dst);
        }
        restore_legacy_jump_velocity(p,source);
        psx_mod_write_word(p->alias_table+3*4,p->records+neutral*56);
        for(unsigned i=0;i<4023;i++)if(native_aliases[i]) {
            unsigned index=native_aliases[i]==3?neutral:native_aliases[i]-8192;
            psx_mod_write_word(p->alias_table+i*4,p->records+index*56);
        }
        psx_mod_write_word(p->header+12,p->alias_table);
        if(tekken3_jun_roster_enabled())psx_mod_write_byte(p->header+1,23);
        /* Native cache headers may be shared by two actors. Keep them intact. */
        psx_mod_write_word(slot,p->header);
        p->native_base=base;p->native_common=common;p->source=source;
        fprintf(stderr,"Jun combat: installed P%u alias table, original=%08X custom=%08X records=%08X\n",player+1,p->original_alias,p->alias_table,p->records);
    }
    unsigned opponent=psx_mod_read_half(0x800a9228+(1-player)*0x188c+0x16);
    /* The shared T3 move keys are 0..18; Jun's new native key is 23.
     * Console-only fighters have no arcade key. Panda/Tiger use their
     * existing shared move headers, just as the native hit resolver does. */
    unsigned source_key=opponent==23?28:opponent<=18?opponent:32;
    for(unsigned i=0;i<dynamic_count;i++) {
        uint32_t address=p->records+dynamic_hits[i].record*56+48;
        unsigned rx=source_key<32 && (dynamic_hits[i].mask&(1u<<source_key))?
                    dynamic_hits[i].alternate:dynamic_hits[i].normal;
        psx_mod_write_word(address,(psx_mod_read_word(address)&65535)|(rx<<16));
    }
    return 1;
}
void __wrap_func_8002D264(CPUState *cpu) {
    unsigned param=(uint16_t)cpu->gpr[5];
    if((cpu->pc==0 || cpu->pc==0x8002d264) && loaded && (param&0x4000)) {
        const ContactGroup *g=NULL;
        for(unsigned i=0;i<group_count;i++)if(groups[i].source==(param&0x3fff))g=&groups[i];
        if(g) {
            for(unsigned i=0;i<count;i++)if(clip_addresses[i]==cpu->gpr[4]) {
                unsigned clip=word(data+32+i*16),match=0;
                for(unsigned k=0;k<g->count;k++)if(g->clips[k]==clip)match=1;
                cpu->gpr[2]=match;cpu->pc=cpu->gpr[31];return;
            }
            cpu->gpr[5]=g->native;
        } else {cpu->gpr[2]=0;cpu->pc=cpu->gpr[31];return;}
    }
    __real_func_8002D264(cpu);
}
void __wrap_func_8002E8D0(CPUState *cpu) {
    if((cpu->pc==0 || cpu->pc==0x8002e8d0) && loaded &&
       psx_mod_read_byte(cpu->gpr[4]+3)==74 && (psx_mod_read_half(cpu->gpr[4]+4)&0x8000)) {
        unsigned alias=psx_mod_read_half(cpu->gpr[4]+4)&0x7fff,match=0;
        uint32_t defender=cpu->gpr[5],attacker=cpu->gpr[6],record=psx_mod_read_word(attacker+0x54);
        for(unsigned p=0;p<2;p++)if(players[p].records && record>=players[p].records &&
            record<players[p].records+count*56 && (record-players[p].records)%56==0) {
            unsigned i=(record-players[p].records)/56;
            match=alias<5515 && source_aliases[alias]==word(data+36+i*16);
        }
        unsigned native=alias==0x125?0xf7:alias==0x45a?0x351:alias==0x47f?0x36f:alias==0xb56?0x85d:0xffff;
        if(native!=0xffff && psx_mod_read_half(attacker+0xa0)==native)match=1;
        match=match && (int16_t)psx_mod_read_half(defender+0x30)<0x2aaa &&
                       (int16_t)psx_mod_read_half(attacker+0x30)<0x2aaa;
        cpu->gpr[2]=match;cpu->pc=cpu->gpr[31];return;
    }
    __real_func_8002E8D0(cpu);
}
void __wrap_func_8006A3BC(CPUState *cpu) {
    if(cpu->pc==0 || cpu->pc==0x8006a3bc) {
        uint32_t actor=cpu->gpr[4];
        for(unsigned p=0;p<2;p++) if(actor==0x800a9228+p*0x188c &&
                tekken3_jun_player_motion_mode(p)==2 && players[p].records) {
            uint32_t record=psx_mod_read_word(actor+0x54),base=players[p].records;
            if(record<base || record>=base+count*56 || (record-base)%56)break;
            uint32_t bones=psx_mod_read_word(record+40);
            /* Arcade 8010AEFC..8010B178 uses two pairs of limb IDs. A
             * zero second ID sweeps the first limb from its previous
             * position. Otherwise the capsule joins two current joints.
             * Core limb numbering 0..17 is unchanged in the PS1 skeleton. */
            for(unsigned k=0;k<2;k++) {
                unsigned end=psx_mod_read_byte(bones+k*2),start=psx_mod_read_byte(bones+k*2+1);
                if(!end)continue;
                uint32_t capsule=actor+0x1ac+k*24;
                uint32_t end_pos=actor+0x908+end*68;
                uint32_t start_pos=start?actor+0x908+start*68:capsule+12;
                for(unsigned axis=0;axis<3;axis++) {
                    psx_mod_write_word(capsule+axis*4,psx_mod_read_word(start_pos+axis*4));
                    psx_mod_write_word(capsule+12+axis*4,psx_mod_read_word(end_pos+axis*4));
                }
            }
            cpu->pc=cpu->gpr[31];return;
        }
    }
    __real_func_8006A3BC(cpu);
}
void __wrap_func_8002CC28(CPUState *cpu) {
    unsigned player=cpu->gpr[4]==0x800aaab4?1:0;
    if((cpu->pc==0 || cpu->pc==0x8002cc28) && cpu->gpr[4]==0x800a9228+player*0x188c && players[player].native_base) {
        unsigned command=psx_mod_read_half(cpu->gpr[5]);
        if(command>=0xe000 && command<0xe000+pattern_count) {
            cpu->gpr[5]=patterns[command-0xe000];cpu->pc=0;
            func_8002CA84(cpu);return;
        }
    }
    __real_func_8002CC28(cpu);
}
void __wrap_func_80059890(CPUState *cpu) {
    /* CPU initialization caches the alias table separately from the actor's
     * move header. If it ran before the import was installed, it still holds
     * Jin's short donor table: Jun's 8192+ move IDs then read outside it.
     * Refresh both native caches immediately before CPU decision-making,
     * including after a round/team transition. Do not reset AI difficulty. */
    if(cpu->pc==0 || cpu->pc==0x80059890) {
        uint32_t actor=cpu->gpr[4];
        for(unsigned p=0;p<2;p++)if(actor==0x800a9228+p*0x188c &&
                psx_mod_read_half(actor+0x18)==23 && ready(p)) {
            unsigned index=psx_mod_read_byte(actor+0x1886);
            if(index<2) {
                psx_mod_write_word(0x8009f2e8+index*4,players[p].alias_table);
                psx_mod_write_word(0x8009f318+index*0x330+12,players[p].alias_table);
            }
        }
    }
    __real_func_80059890(cpu);
}
void __wrap_func_8002CD7C(CPUState *cpu) {
    /* Native CPU command synthesis (800618C0) asks this lookup for a
     * sequence. The human matcher above already understands E000+ IDs,
     * but the original lookup returns NULL for E000+ imported commands.
     * The current pack uses native-format inputs; support the converter's
     * extended format too without changing stock command handling.
     * Resolve only an installed Jun actor; other fighters keep their own
     * commands, including when fighting against Jun. */
    unsigned command=cpu->gpr[4]&65535;
    if((cpu->pc==0 || cpu->pc==0x8002cd7c) && loaded &&
       command>=0xe000 && command<0xe000+pattern_count) {
        uint32_t actor=psx_mod_read_word(0x800afa5c);
        for(unsigned p=0;p<2;p++)if(actor==0x800a9228+p*0x188c &&
                psx_mod_read_half(actor+0x18)==23 &&
                tekken3_jun_player_motion_mode(p)==2 && players[p].native_base) {
            cpu->gpr[2]=patterns[command-0xe000];cpu->pc=cpu->gpr[31];return;
        }
    }
    __real_func_8002CD7C(cpu);
}
void tekken3_jun_combat_tick(void) {
    for(unsigned player=0;player<2;player++) {
        if(tekken3_jun_player_motion_mode(player)==2) {
            if(ready(player)) {
                uint32_t actor=0x800a9228+player*0x188c,record=psx_mod_read_word(actor+0x54);
                unsigned expression=0,frame=psx_mod_read_half(actor+0x58);
                if(source_record(record)) {
                    uint32_t prop=psx_mod_read_word(record+32);
                    for(unsigned i=0;i<256;i++,prop+=4) {
                        unsigned at=psx_mod_read_half(prop),op=psx_mod_read_half(prop+2);
                        if(!at)break;
                        if(op>>8==0x40 && frame>=at && frame<at+(op&255))expression=1;
                    }
                }
                tekken3_jun_face(player,expression);
            }
            continue;
        }
        PlayerCombat *p=&players[player];
        if(p->native_base && psx_mod_read_word(0x800adc20+player*4)==p->header)
            psx_mod_write_word(0x800adc20+player*4,p->native_base);
        p->native_base=0;
    }
}
void __wrap_func_8002D178(CPUState *cpu) {
    unsigned player=cpu->gpr[4]==0x800aaab4?1:0;
    unsigned id=(uint16_t)cpu->gpr[5];
    if((cpu->pc==0 || cpu->pc==0x8002d178) && loaded &&
       cpu->gpr[4]==0x800a9228+player*0x188c && id>=8192 && id<8192+count) {
        int is_jun=tekken3_jun_player_motion_mode(player)==2;
        unsigned native=recovery_aliases[id-8192];
        if(!is_jun && native) {
            /* A victim may borrow Jun's unique hit/throw clip, not her
             * get-up, crouch, or movement command graph. Translating only
             * neutral (ID 3) lets early cancels/get-up attacks leak her
             * entire moveset to the opponent. Resolve recovery against the
             * receiving fighter's own table, in either player slot. */
            cpu->gpr[5]=native-1;
            if(psx_mod_read_half(cpu->gpr[4]+0x1a0)==id)
                psx_mod_write_half(cpu->gpr[4]+0x1a0,native-1);
            __real_func_8002D178(cpu);return;
        }
        /* Unmapped IDs are the original unique victim/paired sequences.
         * Their eventual recovery is intercepted above. Jun mirrors keep
         * their separate per-player source records and full move graphs. */
        unsigned owner=is_jun?player:1-player;
        if(ready(owner)) {
            cpu->gpr[2]=players[owner].records+(id-8192)*56;cpu->pc=cpu->gpr[31];return;
        }
    }
    if((cpu->pc==0 || cpu->pc==0x8002d178) && cpu->gpr[4]==0x800a9228+player*0x188c && ready(player)) {
        static unsigned char reported[4023];
        if(id<4023 && id!=3 && !native_aliases[id] && !reported[id] &&
            psx_mod_read_word(players[player].alias_table+id*4)==players[player].records+neutral*56) {
            reported[id]=1;fprintf(stderr,"Jun combat: unmapped native entry %04X requested by P%u\n",id,player+1);
        }
        if(id==3 || (id>=8192 && id<8192+count)) {
            unsigned index=id==3?neutral:id-8192;
            cpu->gpr[2]=players[player].records+index*56;cpu->pc=cpu->gpr[31];return;
        }
    }
    __real_func_8002D178(cpu);
}
static const uint16_t *pose(uint32_t clip,int frame) {
    if(!loaded || clip<guest)return NULL;
    unsigned index=0;
    while(index<count && clip_addresses[index]!=clip)index++;
    if(index==count)return NULL;
    unsigned offset=clip_offsets[index],n=word(data+offset)&255;
    if((word(data+offset)&0xffffff00)!=0x4a554e00 || word(data+offset+4)!=57 || !n || offset+8+n*114>size)return NULL;
    if(frame<0)frame=0;if((unsigned)frame>=n)frame=n-1;
    return (const uint16_t*)(data+offset+8+frame*114);
}
const uint16_t *tekken3_jun_decoded_pose(uint32_t input) {
    if(psx_mod_read_word(input+8)!=0x504e554a)return NULL;
    uint32_t clip=psx_mod_read_word(input+12);
    return pose(clip,psx_mod_read_half(input+16));
}
static int decode_pose(CPUState *cpu,int full) {
    const uint16_t *p=pose(cpu->gpr[4],(int)cpu->gpr[6]);if(!p)return 0;
    uint32_t out=cpu->gpr[5],angle=p[0],table=0x8001e8c4+((angle>>3)&0x1ffe);
    int32_t s=(int16_t)psx_mod_read_half(table),c=(int16_t)psx_mod_read_half(table+0x800),distance=(int16_t)p[2];
    if(full)for(unsigned i=0;i<49;i++)psx_mod_write_half(out+i*2,0);
    psx_mod_write_half(out,(uint16_t)((s*distance)>>12));
    psx_mod_write_half(out+2,(uint16_t)-(int16_t)p[1]);
    psx_mod_write_half(out+4,(uint16_t)((c*distance)>>12));
    if(full) {
        psx_mod_write_word(out+8,0x504e554a);
        psx_mod_write_word(out+12,cpu->gpr[4]);
        psx_mod_write_half(out+16,(uint16_t)((int)cpu->gpr[6]<0?0:cpu->gpr[6]));
    }
    cpu->pc=cpu->gpr[31];return 1;
}
void __wrap_func_80038B4C(CPUState *cpu) {
    if((cpu->pc==0 || cpu->pc==0x80038b4c) && decode_pose(cpu,1))return;
    __real_func_80038B4C(cpu);
}
void __wrap_func_800389C0(CPUState *cpu) {
    if((cpu->pc==0 || cpu->pc==0x800389c0) && decode_pose(cpu,0))return;
    __real_func_800389C0(cpu);
}

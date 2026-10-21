/* Two-step selection: reserve a fighter locally, then commit its chosen outfit.
 * Only that fighter's controlling pad is captured; the guest never pauses. */
#include "tekken3_outfits.h"
#include "mod_plugins.h"
#include "gpu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
static const Tekken3OutfitEntry defaults[] = {
 {"nina-purple","PURPLE ASSASSIN","nina-purple",5,-1,0x8000},
 {"nina-crimson","CRIMSON LEATHER","nina-crimson",5,-1,0x4000},
 {"nina-white","WHITE SATIN","nina-white",5,T3_SKIN_NINA,0x4000},
 {"xiaoyu-red","RED & GOLD","xiaoyu-red",7,-1,0x8000},
 {"xiaoyu-blue","BLUE RIBBON","xiaoyu-blue",7,-1,0x4000},
 {"xiaoyu-school","SCHOOL UNIFORM","xiaoyu-school",7,-1,0x0008},
 {"xiaoyu-pink","CHERRY BLOSSOM","xiaoyu-pink",7,T3_SKIN_XIAOYU,0x8000},
 {"anna-red","SCARLET SILK","anna-red",18,-1,0x8000},
 {"anna-blue","MIDNIGHT SILK","anna-blue",18,-1,0x4000},
 {"anna-tiger","WHITE TIGER","anna-tiger",18,-1,0x0008},
 {"anna-jessica","JESSICA RABBIT","anna-jessica",18,T3_SKIN_ANNA,0x8000},
 {"kuma-brown","BROWN BEAR","kuma-brown",11,-1,0x8000},
 {"kuma-panda","PANDA","kuma-panda",11,-1,0x4000},
 {"kuma-polar","POLAR BEAR","kuma-polar",11,T3_SKIN_KUMA,0x8000},
 {"jun-arcade-1","BLUE DENIM","jun-arcade-1",23,-1,0x8000},
 {"jun-arcade-2","WHITE WAISTCOAT","jun-arcade-2",23,-1,0x4000},
 {"jun-arcade-3","KARATE GI","jun-arcade-3",23,-1,0x0008},
 {"eddy-original-1","ORIGINAL OUTFIT 1","eddy-original-1",8,-1,0x8000},
 {"eddy-original-2","ORIGINAL OUTFIT 2","eddy-original-2",8,-1,0x4000},
 {"eddy-tiger","TIGER JACKSON","eddy-tiger",8,-1,0x0008},
 {"eddy-monochrome","MONOCHROME","eddy-monochrome",8,T3_SKIN_EDDY,0x8000},
 {"julia-original-1","ORIGINAL OUTFIT 1","julia-original-1",10,-1,0x8000},
 {"julia-original-2","ORIGINAL OUTFIT 2","julia-original-2",10,-1,0x4000},
 {"julia-blue","BLUE TURQUOISE","julia-blue",10,T3_SKIN_JULIA,0x8000},
 {"heihachi-original-1","ORIGINAL OUTFIT 1","heihachi-original-1",13,-1,0x8000},
 {"heihachi-original-2","ORIGINAL OUTFIT 2","heihachi-original-2",13,-1,0x4000},
 {"heihachi-tiger-coat","TIGER COAT","heihachi-tiger-coat",13,T3_SKIN_HEIHACHI,0x4000}
};
static Tekken3OutfitEntry *catalog;
static int catalog_count,available[T3_SKIN_COUNT];
static uint32_t imported_characters;
static int character_override[2]={-1,-1};
static const int skin_characters[T3_SKIN_COUNT]={5,7,18,11,8,10,13};
static int selecting,character[2]={-1,-1},connected[2],locked[2];
static int choice[2][24],committed[2]={-1,-1},pending[2];
static uint16_t confirmation[2],previous[2]={0xffff,0xffff},suppress[2];
static int menu=-1; /* Legacy debug API; there is no modal owner anymore. */
static int browsing[2],team_select,team_count[2]={-1,-1};
static int team_skins[2][24],team_session;
static uint32_t borrowed_flags;
static int owner[2]={0,1},can_select[2],native_phase[2]={-1,-1},cpu_panel[2];
static Tekken3OutfitEntry stock[21][3];
static int stock_initialized;
static const Tekken3OutfitEntry *stock_entry(int cid,int index) {
 if(cid<0 || cid>=21 || index<0 || index>=3)return NULL;
 if(index==2 && !(psx_mod_read_word(0x80097ef4u)&(1u<<cid)))return NULL;
 if(!stock_initialized) {
  for(int c=0;c<21;c++)for(int i=0;i<3;i++) {
   Tekken3OutfitEntry *e=&stock[c][i];e->character=c;e->skin=-1;
   e->confirm=i==0?0x8000:i==1?0x4000:8;
   snprintf(e->id,sizeof e->id,"stock-%d-%d",c,i+1);
   snprintf(e->name,sizeof e->name,"ORIGINAL OUTFIT %d",i+1);
  }
  stock_initialized=1;
 }
 return &stock[cid][index];
}
static int valid_entry(const Tekken3OutfitEntry *e) {
 if(e->character<0 || e->character>=24 || e->skin < -1 || e->skin>=T3_SKIN_COUNT)return 0;
 if(e->skin>=0 && skin_characters[e->skin]!=e->character)return 0;
 if(e->confirm!=0x8000 && e->confirm!=0x4000 && e->confirm!=8)return 0;
 if(!e->id[0] || !e->name[0])return 0;
 for(const char *p=e->id;*p;p++)if(!isalnum((unsigned char)*p) && *p!='-' && *p!='_')return 0;
 for(const char *p=e->art;*p;p++)if(!isalnum((unsigned char)*p) && *p!='-' && *p!='_')return 0;
 for(const char *p=e->name;*p;p++)if(!isalnum((unsigned char)*p) && !strchr(" -&'.",*p))return 0;
 return 1;
}
int tekken3_outfits_load_catalog(const char *path) {
 if(selecting || menu>=0)return 0;
 FILE *f=path?fopen(path,"r"):NULL;Tekken3OutfitEntry *rows=NULL;int count=0;
 if(f) {
  char line[512];
  while(fgets(line,sizeof line,f)) {
   Tekken3OutfitEntry e={0};unsigned mask=0;int end=0;
   if(line[0]=='#' || line[0]=='\n' || line[0]=='\r')continue;
   if(sscanf(line,"%47[^|]|%d|%39[^|]|%x|%d|%63[^\r\n]%n",e.id,&e.character,e.name,&mask,&e.skin,e.art,&end)!=6 || !end || (line[end] && line[end]!='\r' && line[end]!='\n') || mask>65535)continue;
   e.confirm=(uint16_t)mask;if(!valid_entry(&e))continue;
   int duplicate=0;for(int i=0;i<count;i++)if(!strcmp(rows[i].id,e.id))duplicate=1;
   if(duplicate)continue;
   Tekken3OutfitEntry *next=(Tekken3OutfitEntry*)realloc(rows,(size_t)(count+1)*sizeof *rows);
   if(!next)break;rows=next;rows[count++]=e;
  }
  fclose(f);
 }
 free(catalog);catalog=rows;catalog_count=count;memset(choice,0,sizeof choice);return count;
}
const Tekken3OutfitEntry *tekken3_outfits_entry(int cid,int index) {
 if(cid>=21 && (cid>=24 || !(imported_characters&(1u<<cid))))return NULL;
 const Tekken3OutfitEntry *rows=catalog_count?catalog:defaults;
 int n=catalog_count?catalog_count:(int)(sizeof defaults/sizeof *defaults);
 if(index<0)return NULL;
 int found=0;
 for(int i=0;i<n;i++)if(rows[i].character==cid) {
  found=1;
  if((rows[i].skin<0 || available[rows[i].skin]) && !index--)return &rows[i];
 }
 return found?NULL:stock_entry(cid,index);
}
int tekken3_outfits_count(int cid) {int n=0;while(tekken3_outfits_entry(cid,n))n++;return n;}
void tekken3_outfits_set_available(int skin,int on) {if(skin>=0 && skin<T3_SKIN_COUNT)available[skin]=!!on;}
void tekken3_outfits_set_character_available(int cid,int on) {
 if(cid<21 || cid>=24)return;
 if(on)imported_characters|=1u<<cid;else imported_characters&=~(1u<<cid);
}
void tekken3_outfits_set_character_override(int player,int cid) {
 if(player>=0 && player<2)character_override[player]=cid>=0 && cid<24?cid:-1;
}
int tekken3_outfits_available(void) {
#ifdef TEKKEN3_LAUNCHER
 return 1; /* Stock costume selection works with every optional mod disabled. */
#else
 if(imported_characters)return 1;
 for(int i=0;i<T3_SKIN_COUNT;i++)if(available[i])return 1;
 return 0;
#endif
}
void tekken3_outfits_update(int active,int c1,int c2) {
 active=!!active && tekken3_outfits_available();
 if(active && !selecting)for(int p=0;p<2;p++){locked[p]=0;committed[p]=-1;pending[p]=0;browsing[p]=0;}
 if(!active){menu=-1;pending[0]=pending[1]=0;browsing[0]=browsing[1]=0;}selecting=active;
 if(active) {
  int ids[2]={c1,c2};
  for(int p=0;p<2;p++) {
   if(ids[p]!=character[p]){locked[p]=0;pending[p]=0;browsing[p]=0;}
   character[p]=ids[p];
   if(ids[p]>=0 && ids[p]<24 && choice[p][ids[p]]>=tekken3_outfits_count(ids[p]))choice[p][ids[p]]=0;
  }
 }
}
void tekken3_outfits_sync(void) {
 int active=gpu_tekken3_selector_active();
#ifdef TEKKEN3_LAUNCHER
 unsigned screen=psx_mod_read_word(0x800ae204u);
 int cabinet=screen==9 && psx_mod_read_word(0x8010ff4cu)==0x27bdffd0u &&
     psx_mod_read_word(0x8010ff50u)==0x3c028012u;
 /* The native timer is ceil(frames / tick_rate). Replace only the verified
  * 20 * tick_rate initializer with 99 * tick_rate, not the decrement loop.
  * This overlay is interpreted and write_code_word invalidates its cache. */
 if(cabinet && psx_mod_read_word(0x8010dd48u)==0x00031080u &&
    psx_mod_read_word(0x8010dd4cu)==0x00431021u &&
    psx_mod_read_word(0x8010dd50u)==0x00021080u) {
   psx_mod_write_code_word(0x8010dd48u,0x24020063u); /* li v0,99 */
   psx_mod_write_code_word(0x8010dd4cu,0x00430018u); /* mult v0,v1 */
   psx_mod_write_code_word(0x8010dd50u,0x00001012u); /* mflo v0 */
   /* The first VBlank can arrive just after the overlay initialized. */
   uint32_t rate=psx_mod_read_word(0x80118640u),left=psx_mod_read_word(0x8011863cu);
   if(rate>=60 && rate<=120 && left>0 && left<=rate*20)
     psx_mod_write_word(0x8011863cu,rate*99);
 }
 int was_team=team_select;
 team_select=screen==10 && psx_mod_read_word(0x80053000u)==0x27bdffd0u;
 active=(cabinet && psx_mod_read_half(0x800ae224u)<=1) || team_select;
 if(team_select && !was_team) {
   for(int p=0;p<2;p++){team_count[p]=-1;for(int c=0;c<24;c++)team_skins[p][c]=-1;}
   team_session=1;
 } else if(cabinet)team_session=0;
#endif
 int ids[2];
 for(int p=0;p<2;p++) {
   int phase=-1,next_owner=p,manual=active,is_cpu=0;
   ids[p]=character_override[p]>=0?character_override[p]:psx_mod_read_byte(0x80098106u+p);
#ifdef TEKKEN3_LAUNCHER
   if(cabinet) {
     uint32_t panel=0x8011864cu+p*0x7cu;
     phase=(int)psx_mod_read_word(panel);
     ids[p]=(int)psx_mod_read_word(panel+0x1c);
     /* Native phase 1 reads this pad; phase 3 selects the CPU with the
      * opposite pad (8010DE70 / 8010E030). Do not infer from connectivity. */
     manual=phase==1 || phase==3;is_cpu=phase==3;
     if(is_cpu)next_owner=1-p;
   }
   if(team_select) {
     uint32_t state=0x800b8d70u+p*0xacu;
     unsigned team_phase=psx_mod_read_word(state),x=psx_mod_read_word(state+8),y=psx_mod_read_word(state+12);
     phase=(int)team_phase;manual=phase==2 || phase==3 || phase==7;
     is_cpu=phase==7;if(is_cpu)next_owner=1-p;
     uint32_t op=psx_mod_read_word(0x80052e24u),table=0x80022768u;
     int columns=7;
     if((op&0xffff0000u)==0x3c030000u){table=(op&65535u)<<16;columns=8;}
     ids[p]=-1;
     if(manual && x<(unsigned)columns && y<3 &&
        (table==0x80022768u || (table>=0x9f000000u && table<0xa0000000u))) {
       int cid=psx_mod_read_half(table+(y*columns+x)*6+4)/4;
       if(cid<24 && (psx_mod_read_word(state+36)&(1u<<cid)))ids[p]=cid;
     }
     int count=(int)psx_mod_read_word(state+44);
     if(count!=team_count[p]) {
       team_count[p]=count;pending[p]=0;locked[p]=0;browsing[p]=0;
     }
   }
#endif
   if(native_phase[p]!=phase || owner[p]!=next_owner || !manual) {
     /* End confirmation immediately when native code consumes it. Otherwise
      * a held synthetic attack could select the next CPU/team fighter. */
     pending[p]=0;browsing[p]=0;locked[p]=0;
   }
   native_phase[p]=phase;owner[p]=next_owner;can_select[p]=manual;cpu_panel[p]=is_cpu;
 }
 tekken3_outfits_update(active,ids[0],ids[1]);
 /* SLUS-00402 selector 8010DAE0 tests bit(character) at 80097EF4 for
  * Start/costume 2. Borrow just that bit and restore it after selection. */
 uint32_t flags=psx_mod_read_word(0x80097ef4u);
 if(selecting) {
  for(int p=0;p<2;p++)if(pending[p] && (confirmation[p]==8 || (team_select && confirmation[p]==0x1000)) && character[p]>=0 && character[p]<24){uint32_t bit=1u<<character[p];borrowed_flags|=bit & ~flags;flags|=bit;}
  if(flags!=psx_mod_read_word(0x80097ef4u))psx_mod_write_word(0x80097ef4u,flags);
 }else if(borrowed_flags){psx_mod_write_word(0x80097ef4u,flags & ~borrowed_flags);borrowed_flags=0;}
}
void tekken3_outfits_connect(int p,int on) {
 if(p<0 || p>1)return;connected[p]=!!on;
 if(!on){previous[p]=0xffff;suppress[p]=0;
  for(int f=0;f<2;f++)if(owner[f]==p){browsing[f]=0;pending[f]=0;locked[f]=0;}
 }
}
void tekken3_outfits_tick(void) {
 for(int p=0;p<2;p++)if(pending[p]>0)pending[p]--;
}
int tekken3_outfits_open(int p) {
 if(p<0 || p>1 || !selecting || !can_select[p] || !connected[owner[p]] || locked[p] || !tekken3_outfits_count(character[p]))return 0;
 browsing[p]=1;return 1;
}
int tekken3_outfits_menu_player(void){return menu;}
int tekken3_outfits_cycle(int p,int direction) {
 if(p<0 || p>1 || !direction || !browsing[p] || !tekken3_outfits_open(p))return 0;
 int n=tekken3_outfits_count(character[p]);if(!n)return 0;
 int *c=&choice[p][character[p]];*c=(*c+(direction>0?1:n-1))%n;return 1;
}
void tekken3_outfits_close(int accept) {
 if(!accept)for(int p=0;p<2;p++)if(browsing[p]) {
  browsing[p]=0;locked[p]=0;suppress[owner[p]]|=(uint16_t)~previous[owner[p]];
 }
}
int tekken3_outfits_captures_input(int pad) {
 if(pad<0 || pad>1 || !selecting)return 0;
 for(int f=0;f<2;f++)if(owner[f]==pad && (browsing[f] || pending[f]))return 1;
 return suppress[pad]!=0;
}
uint16_t tekken3_outfits_input(int pad,uint16_t buttons) {
 if(pad<0 || pad>1)return buttons;
 uint16_t pressed=(uint16_t)~buttons,edges=previous[pad]&pressed;
 previous[pad]=buttons;suppress[pad]&=pressed;
 if(!selecting || !connected[pad])return buttons;
 buttons|=suppress[pad];edges&=(uint16_t)~suppress[pad];
 int p=-1;
 for(int f=0;f<2;f++)if(can_select[f] && owner[f]==pad){p=f;break;}
 if(p<0)return buttons;
 if(pending[p]>0)return (uint16_t)~confirmation[p];
 if(tekken3_outfits_count(character[p])){
  if(locked[p])return buttons;
  if(!browsing[p]) {
   if(edges&(team_select?0xf000:0xf008)) {
    /* The first button chooses ONLY the character, never its costume. */
    if(tekken3_outfits_open(p)){suppress[pad]|=pressed;return 0xffff;}
   }
   return buttons;
  }
  if(edges&0x2001) { /* Circle/B or Select: undo this local character choice. */
   browsing[p]=0;locked[p]=0;committed[p]=-1;
   suppress[pad]|=pressed;return 0xffff;
  }
  if(edges&(0x0080|0x0400))tekken3_outfits_cycle(p,-1); /* Left/L1 */
  else if(edges&(0x0020|0x0800))tekken3_outfits_cycle(p,1); /* Right/R1 */
  if(edges&0xd008) { /* Cross/A, Square, Triangle or Start confirms this card. */
   const Tekken3OutfitEntry *e=tekken3_outfits_entry(character[p],choice[p][character[p]]);
   committed[p]=-1;locked[p]=1;
   if(e) {
     committed[p]=e->skin;
     /* Team Battle's Start randomizes the team; Triangle is costume three. */
     confirmation[p]=team_select && e->confirm==8?0x1000:e->confirm;
     /* Unlock before returning this first injected sample. Waiting until
      * next sync lets Team Battle consume Triangle as costume zero. */
     if(e->confirm==8) {
       uint32_t bit=1u<<character[p],flags=psx_mod_read_word(0x80097ef4u);
       borrowed_flags|=bit&~flags;
       if(!(flags&bit))psx_mod_write_word(0x80097ef4u,flags|bit);
     }
     pending[p]=24;suppress[pad]|=pressed;browsing[p]=0;
     if(team_select)team_skins[p][character[p]]=e->skin;
     return (uint16_t)~confirmation[p];
   }
   if(team_select)team_skins[p][character[p]]=-1;
  }
  return 0xffff; /* The highlighted fighter cannot move while choosing art. */
 }
 return buttons;
}
Tekken3OutfitView tekken3_outfits_view(int p) {
 Tekken3OutfitView v={0,-1,0,0,0,"ORIGINAL",0,0,0,0,0};if(p<0 || p>1)return v;
 v.character=character[p];v.visible=selecting && can_select[p] && connected[owner[p]] && browsing[p] && character[p]>=0;v.locked=locked[p];v.menu=0;
 v.owner=owner[p];v.cpu=cpu_panel[p];
 v.count=tekken3_outfits_count(v.character);v.has_extra=v.count>0;
 if(v.character>=0 && v.character<24)v.index=choice[p][v.character];
 const Tekken3OutfitEntry *e=tekken3_outfits_entry(v.character,v.index);if(e){v.name=e->name;v.custom=e->skin>=0;}return v;
}
int tekken3_outfits_skin_enabled(int skin,int cy) {
 if(skin<0 || skin>=T3_SKIN_COUNT || !available[skin])return 0;
 /* Each fighter owns four CLUT rows; some costumes use more than two. */
 int p=cy>=504 && cy<=507?0:cy>=508 && cy<=511?1:-1;
 if(p<0)return 0;
 if(team_session) {
   int cid=psx_mod_read_half(0x800a9240u+p*0x188cu);
   return cid>=0 && cid<24 && team_skins[p][cid]==skin;
 }
 return committed[p]==skin;
}

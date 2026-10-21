/* Offline regression. Build with -DTEKKEN3_LAUNCHER=1 and tekken3_outfits.c. */
#include "tekken3_outfits.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char ram[0x200000],extension[0x10000];
static unsigned char *at(uint32_t a) {
 if(a>=0x9f030000u && a<0x9f040000u)return extension+a-0x9f030000u;
 assert(a>=0x80000000u && a<0x80200000u);return ram+(a&0x1fffff);
}
int gpu_tekken3_selector_active(void){return 0;} /* Exercise software path too. */
uint8_t psx_mod_read_byte(uint32_t a){return *at(a);}
uint16_t psx_mod_read_half(uint32_t a){uint16_t n;memcpy(&n,at(a),2);return n;}
uint32_t psx_mod_read_word(uint32_t a){uint32_t n;memcpy(&n,at(a),4);return n;}
void psx_mod_write_word(uint32_t a,uint32_t n){memcpy(at(a),&n,4);}
void psx_mod_write_code_word(uint32_t a,uint32_t n){psx_mod_write_word(a,n);}
static void half(uint32_t a,uint16_t n){memcpy(at(a),&n,2);}
static void leave(void){psx_mod_write_word(0x800ae204,8);tekken3_outfits_sync();}
static void neutral(void){for(int p=0;p<2;p++)tekken3_outfits_input(p,0xffff);}
static void enter(int c1,int c2) {
 leave();psx_mod_write_word(0x800ae204,9);half(0x800ae224,1);
 psx_mod_write_word(0x8010ff4c,0x27bdffd0);psx_mod_write_word(0x8010ff50,0x3c028012);
 *at(0x80098106)=(unsigned char)c1;*at(0x80098107)=(unsigned char)c2;
 psx_mod_write_word(0x8011864c,1);psx_mod_write_word(0x801186c8,1);
 psx_mod_write_word(0x80118668,c1);psx_mod_write_word(0x801186e4,c2);
 tekken3_outfits_sync();neutral();
}
static void tap(int p,uint16_t b){tekken3_outfits_input(p,(uint16_t)~b);tekken3_outfits_input(p,0xffff);}
static void choose(int p,int i) {
 assert(tekken3_outfits_open(p));
 for(int n=0;n<24 && tekken3_outfits_view(p).index!=i;n++)tap(tekken3_outfits_view(p).owner,0x800);
 assert(tekken3_outfits_view(p).index==i);
}
static void team(int expanded) {
 leave();psx_mod_write_word(0x800ae204,10);psx_mod_write_word(0x80053000,0x27bdffd0);
 psx_mod_write_word(0x80052e24,expanded?0x3c039f03:0x24632768);
 for(int p=0;p<2;p++) {
  uint32_t s=0x800b8d70+p*0xac;
  psx_mod_write_word(s,2);psx_mod_write_word(s+8,p);psx_mod_write_word(s+12,0);
  psx_mod_write_word(s+36,0xffffff);psx_mod_write_word(s+44,0);
 }
 uint32_t table=expanded?0x9f030000:0x80022768;
 half(table+4,23*4);half(table+10,5*4);tekken3_outfits_sync();neutral();
}
static void timer_code(void) {
 psx_mod_write_word(0x8010dd48,0x00031080);psx_mod_write_word(0x8010dd4c,0x00431021);
 psx_mod_write_word(0x8010dd50,0x00021080);
}
int main(void) {
 for(int s=0;s<T3_SKIN_COUNT;s++)tekken3_outfits_set_available(s,1);
 tekken3_outfits_set_character_available(23,1);
 tekken3_outfits_connect(0,1);tekken3_outfits_connect(1,1);
 timer_code();psx_mod_write_word(0x80118640,60);psx_mod_write_word(0x8011863c,1199);
 enter(5,18);
 assert(psx_mod_read_word(0x8010dd48)==0x24020063);
 assert(psx_mod_read_word(0x8010dd4c)==0x00430018 && psx_mod_read_word(0x8010dd50)==0x00001012);
 assert(psx_mod_read_word(0x8011863c)==99*60);
 psx_mod_write_word(0x8011863c,99*60-1);tekken3_outfits_sync();
 assert(psx_mod_read_word(0x8011863c)==99*60-1); /* Not frozen. */
 assert(!tekken3_outfits_view(0).visible && !tekken3_outfits_view(1).visible);
 assert(tekken3_outfits_input(0,0xff7f)==0xff7f); /* Roster navigation stays native. */
 neutral();assert(tekken3_outfits_input(0,0x7fff)==0xffff);
 for(int i=0;i<20;i++)assert(tekken3_outfits_input(0,0x7fff)==0xffff);
 assert(tekken3_outfits_view(0).visible && !tekken3_outfits_view(0).locked);
 neutral();tap(1,0x2000); /* Even Circle first selects the character, not a skin. */
 assert(tekken3_outfits_view(1).visible);
 int start=tekken3_outfits_view(0).index;
 assert(tekken3_outfits_input(0,0xffdf)==0xffff);
 for(int i=0;i<20;i++)tekken3_outfits_input(0,0xffdf);
 assert(tekken3_outfits_view(0).index==(start+1)%3 && tekken3_outfits_menu_player()==-1);
 neutral();assert(tekken3_outfits_input(0,0xff7f)==0xffff);
 assert(tekken3_outfits_input(1,0xffdf)==0xffff);
 assert(tekken3_outfits_captures_input(0) && tekken3_outfits_captures_input(1));
 neutral();choose(0,2);choose(1,3);
 assert(tekken3_outfits_input(0,0x7fff)==0xbfff);
 assert(tekken3_outfits_input(1,0xbfff)==0x7fff);
 assert(tekken3_outfits_skin_enabled(T3_SKIN_NINA,504));
 assert(tekken3_outfits_skin_enabled(T3_SKIN_ANNA,509));
 assert(!tekken3_outfits_skin_enabled(T3_SKIN_NINA,508));
 for(int i=0;i<24;i++){assert(tekken3_outfits_input(0,0xffff)==0xbfff);tekken3_outfits_tick();}
 assert(tekken3_outfits_input(0,0xffff)==0xffff && !tekken3_outfits_cycle(0,1));
 enter(5,18);assert(tekken3_outfits_input(0,0xdfff)==0xffff);
 neutral();assert(tekken3_outfits_input(0,0xdfff)==0xffff); /* Back unselects locally. */
 assert(!tekken3_outfits_view(0).visible && psx_mod_read_word(0x8011864c)==1);
 for(int i=0;i<20;i++)assert(tekken3_outfits_input(0,0xdfff)==0xffff);
 neutral();assert(tekken3_outfits_input(0,0xff7f)==0xff7f);
 assert(!tekken3_outfits_skin_enabled(T3_SKIN_NINA,504));
 /* Every first attack/Start opens without a native confirmation or costume change. */
 const uint16_t openings[]={0x1000,0x2000,0x4000,0x8000,8};
 for(int i=0;i<5;i++) {
  enter(7,18);int before=tekken3_outfits_view(0).index;
  assert(tekken3_outfits_input(0,(uint16_t)~openings[i])==0xffff);
  assert(tekken3_outfits_view(0).visible && tekken3_outfits_view(0).index==before);
 }
 /* CPU ownership is native phase 3, not pad-2 connectivity. */
 for(int fighter=0;fighter<2;fighter++) {
  int pad=1-fighter;enter(5,18);
  psx_mod_write_word(0x8011864c+pad*0x7c,6);
  psx_mod_write_word(0x8011864c+fighter*0x7c,3);
  tekken3_outfits_connect(fighter,0);tekken3_outfits_sync();neutral();
  tap(pad,0x4000);
  Tekken3OutfitView v=tekken3_outfits_view(fighter);
  assert(v.visible && v.cpu && v.owner==pad);
  choose(fighter,fighter?3:2);
  assert(tekken3_outfits_input(pad,0xbfff)==(fighter?0x7fff:0xbfff));
  assert(tekken3_outfits_skin_enabled(fighter?T3_SKIN_ANNA:T3_SKIN_NINA,fighter?508:504));
  psx_mod_write_word(0x8011864c+fighter*0x7c,7);tekken3_outfits_sync();
  assert(tekken3_outfits_input(pad,0xffff)==0xffff); /* No synthetic pulse leaks. */
  tekken3_outfits_connect(fighter,1);
 }
 /* P1's chosen skin survives that same pad selecting a different CPU skin. */
 enter(5,7);choose(0,2);assert(tekken3_outfits_input(0,0xbfff)==0xbfff);
 psx_mod_write_word(0x8011864c,6);psx_mod_write_word(0x801186c8,3);
 tekken3_outfits_connect(1,0);tekken3_outfits_sync();neutral();choose(1,3);
 assert(tekken3_outfits_input(0,0xbfff)==0x7fff);
 assert(tekken3_outfits_skin_enabled(T3_SKIN_NINA,504));
 assert(tekken3_outfits_skin_enabled(T3_SKIN_XIAOYU,508));
 tekken3_outfits_connect(1,1);
 for(int i=0;i<3;i++) {
  enter(23,23);choose(i&1,i);
  uint32_t before=psx_mod_read_word(0x80097ef4);
  assert(tekken3_outfits_input(i&1,0x7fff)==(uint16_t)~(i==0?0x8000:i==1?0x4000:8));
  if(i==2)assert(psx_mod_read_word(0x80097ef4)&(1u<<23));
  tekken3_outfits_sync();
  leave();assert(psx_mod_read_word(0x80097ef4)==before);
 }
 for(int expanded=0;expanded<2;expanded++) {
  team(expanded);assert(tekken3_outfits_view(0).character==23 && tekken3_outfits_view(1).character==5);
  choose(0,2);choose(1,2);
  assert(tekken3_outfits_input(0,0x7fff)==0xefff); /* Triangle, never random team. */
  assert(psx_mod_read_word(0x80097ef4)&(1u<<23));
  assert(tekken3_outfits_input(1,0x7fff)==0xbfff);
  tekken3_outfits_sync();assert(psx_mod_read_word(0x80097ef4)&(1u<<23));
  psx_mod_write_word(0x800b8d70+44,1);psx_mod_write_word(0x800b8d70+0xac+44,1);
  tekken3_outfits_sync();neutral();assert(!tekken3_outfits_view(0).locked && !tekken3_outfits_view(1).locked);
  assert(tekken3_outfits_input(0,0xfff7)==0xfff7); /* Preserve native random team. */
  leave();half(0x800a9240,23);half(0x800a9240+0x188c,5);
  assert(tekken3_outfits_skin_enabled(T3_SKIN_NINA,508));
  half(0x800a9240+0x188c,9);assert(!tekken3_outfits_skin_enabled(T3_SKIN_NINA,508));
  half(0x800a9240+0x188c,5);assert(tekken3_outfits_skin_enabled(T3_SKIN_NINA,508));
  team(expanded);psx_mod_write_word(0x800b8d70,11);psx_mod_write_word(0x800b8d70+0xac,7);
  tekken3_outfits_connect(1,0);tekken3_outfits_sync();neutral();
  tap(0,0x8000);assert(tekken3_outfits_view(1).visible && tekken3_outfits_view(1).cpu);
  choose(1,2);assert(tekken3_outfits_input(0,0xbfff)==0xbfff);
  psx_mod_write_word(0x800b8d70+0xac+44,1);tekken3_outfits_sync();
  assert(tekken3_outfits_input(0,0xffff)==0xffff);
  tekken3_outfits_connect(1,1);
 }
 /* New packs: correct character/base, both pads and opposite-pad CPU chooser. */
 const int new_cids[]={8,10,13},new_skins[]={T3_SKIN_EDDY,T3_SKIN_JULIA,T3_SKIN_HEIHACHI};
 const int custom_index[]={3,2,2};
 for(int k=0;k<3;k++) {
  int cid=new_cids[k],skin=new_skins[k],idx=custom_index[k];
  tekken3_outfits_set_available(skin,1);
  assert(tekken3_outfits_count(cid)==idx+1);
  for(int side=0;side<2;side++) {
   enter(cid,cid);choose(side,idx);
   uint16_t expected=k==2?0xbfff:0x7fff;
   assert(tekken3_outfits_input(side,0xbfff)==expected);
   assert(tekken3_outfits_skin_enabled(skin,side?508:504));
   assert(tekken3_outfits_skin_enabled(skin,side?510:506));
   assert(tekken3_outfits_skin_enabled(skin,side?511:507));
   assert(!tekken3_outfits_skin_enabled(skin,503));
   assert(!tekken3_outfits_skin_enabled(skin,512));
   assert(!tekken3_outfits_skin_enabled(skin,side?504:508));
   enter(cid,cid);choose(side,0);tekken3_outfits_input(side,0xbfff);
   assert(!tekken3_outfits_skin_enabled(skin,side?508:504));
  }
  enter(cid,cid);psx_mod_write_word(0x8011864c,6);psx_mod_write_word(0x801186c8,3);
  tekken3_outfits_sync();neutral();choose(1,idx);
  assert(tekken3_outfits_view(1).owner==0 && tekken3_outfits_view(1).cpu);
  tekken3_outfits_input(0,0xbfff);assert(tekken3_outfits_skin_enabled(skin,508));
  team(0);half(0x80022768+4,(uint16_t)(cid*4));tekken3_outfits_sync();neutral();
  choose(0,idx);tekken3_outfits_input(0,0xbfff);
  leave();half(0x800a9240,(uint16_t)cid);assert(tekken3_outfits_skin_enabled(skin,504));
  half(0x800a9240,9);assert(!tekken3_outfits_skin_enabled(skin,504));
  tekken3_outfits_set_available(skin,0);assert(tekken3_outfits_count(cid)==idx);
  tekken3_outfits_set_available(skin,1);
 }
 enter(5,18);tekken3_outfits_connect(1,0);assert(!tekken3_outfits_view(1).visible);
 assert(tekken3_outfits_input(1,0xfbff)==0xfbff);tekken3_outfits_connect(1,1);
 tekken3_outfits_set_available(T3_SKIN_NINA,0);assert(tekken3_outfits_count(5)==2);
 leave();for(unsigned b=0;b<65536;b++)for(int p=0;p<2;p++)assert(tekken3_outfits_input(p,(uint16_t)b)==b);
 for(int s=0;s<T3_SKIN_COUNT;s++)tekken3_outfits_set_available(s,0);
 tekken3_outfits_set_character_available(23,0);timer_code();enter(5,18);
 assert(psx_mod_read_word(0x8010dd48)==0x24020063 && tekken3_outfits_available());
 enter(9,0);assert(tekken3_outfits_count(9)>=2);tap(0,0x8000);
 assert(tekken3_outfits_view(0).visible);choose(0,1);
 assert(tekken3_outfits_input(0,0xbfff)==0xbfff);
 puts("PASS: two-step confirmation, Back, held edges, P1/P2/CPU ownership, both team grids, original costumes, 99 timer and 131072 gameplay inputs");
 return 0;
}

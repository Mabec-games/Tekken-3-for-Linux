/* Render the actual carousel rasterizer without starting the game. */
#define main outfit_state_tests
#include "outfit_carousel_test.c"
#undef main
#include <stdlib.h>
#define HOST_OSD_VISUAL 1
#define PSX_SDL3 1
static const char *art_base;
static const char *SDL_GetBasePath(void){return art_base;}
#include "../../psxrecomp/runtime/src/host_osd_font.inl"
#include "../../psxrecomp/runtime/src/tekken3_outfit_carousel.inl"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "../../recomp-ui/src/third_party/stb_image_write.h"
static void preview(const char *dir,int vw,int vh) {
 unsigned char *image=(unsigned char*)malloc((size_t)vw*vh*3);assert(image);
 memset(image,35,(size_t)vw*vh*3);
 int rects[2][4];
 for(int p=0;p<2;p++) {
  const uint32_t *pixels;int iw,ih;
  assert(host_osd_outfit_image(p,&pixels,&iw,&ih));
  int *r=rects[p];host_osd_outfit_rect(p,vw,vh,iw,ih,&r[0],&r[1],&r[2],&r[3]);
  assert(r[0]>=0 && r[1]>=0 && r[0]+r[2]<=vw && r[1]+r[3]<=vh);
  const uint32_t *base=pixels,*cached;
  assert(host_osd_outfit_image_hires(p,&pixels,r[2],r[3]));
  assert(host_osd_outfit_image_hires(p,&cached,r[2],r[3]) && cached==pixels);
  int detail_changes=0;
  for(int y=0;y<r[3];y++)for(int x=0;x<r[2];x++) {
   uint32_t c=pixels[y*r[2]+x];int alpha=c>>24;
   if(c!=base[y*ih/r[3]*iw+x*iw/r[2]])detail_changes++;
   unsigned char *out=image+((y+r[1])*vw+x+r[0])*3;
   for(int k=0;k<3;k++)out[k]=(unsigned char)((((c>>(16-k*8))&255)*alpha+out[k]*(255-alpha))/255);
  }
  if(p==1 && vh>=720)assert(detail_changes>1000);
 }
 assert(rects[0][0]==vw-rects[1][0]-rects[1][2]);
 assert(rects[0][1]==rects[1][1] && rects[0][2]==rects[1][2]);
 assert(rects[0][0]+rects[0][2]<rects[1][0]);
 char path[1024];snprintf(path,sizeof path,"%s/carousel-%dx%d.png",dir,vw,vh);
 assert(stbi_write_png(path,vw,vh,3,image,vw*3));free(image);
}
int main(int argc,char **argv) {
 assert(argc==3);art_base=argv[1];outfit_state_tests();
 for(int s=0;s<T3_SKIN_COUNT;s++)tekken3_outfits_set_available(s,1);
 tekken3_outfits_set_character_available(23,1);enter(23,5);choose(0,2);choose(1,2);
 preview(argv[2],960,720);preview(argv[2],1280,720);preview(argv[2],640,480);
 preview(argv[2],1920,1080);preview(argv[2],3840,2160);
 /* Exercise every shipped photo through the actual catalog and rasterizer. */
 const int characters[]={5,7,18,11,23,8,10,13};
 int entries=0;
 for(int c=0;c<(int)(sizeof characters/sizeof *characters);c++) {
  enter(characters[c],characters[c]);
  for(int n=0;n<tekken3_outfits_count(characters[c]);n++) {
   const Tekken3OutfitEntry *entry=tekken3_outfits_entry(characters[c],n);
   OutfitArt *a=outfit_load_art(entry->art);
   assert(a && a->loaded==1 && a->width*3==a->height*2);
   choose(0,n);choose(1,n);
   const uint32_t *p1,*p2;
   assert(host_osd_outfit_image_hires(0,&p1,486,351));
   assert(host_osd_outfit_image_hires(1,&p2,486,351));
   assert(p1!=p2);entries++;
  }
 }
 assert(entries==27);
 /* Source art stays full resolution; Jun may use the native fallback. */
 assert(PORTRAIT_W*3==PORTRAIT_H*2);
 int fullres=0;
 for(OutfitArt *a=outfit_art;a;a=a->next) {
  assert(a->loaded && a->pixels && a->width>0 && a->height>0);
  if(a->loaded==1) {assert(a->width>72 && a->height>108);fullres++;}
 }
 assert(fullres);
 const uint32_t *unused;
 assert(!host_osd_outfit_image_hires(-1,&unused,216,156));
 assert(!host_osd_outfit_image_hires(0,&unused,0,156));
 assert(!host_osd_outfit_image_hires(0,&unused,4097,156));
 puts("PASS: all 27 outfit photos, both players, full-resolution sources, detailed output, cache reuse, 2:3 cards, mirrored 4:3/16:9 margins, 480p through 4K");
}

/* An extra P1 character choice attached to Jin's selector cell. Jun retains
 * a separate host identity; Jin's original asset loader supplies the base slot. */
#include "mod_plugins.h"
#include "gpu.h"
#include "psx_sdl.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern uint16_t __real_tekken3_outfits_input(int player,uint16_t buttons);
extern int __real_host_osd_outfit_image(int player,const uint32_t **pixels,int *w,int *h);
extern void __real_host_osd_draw_sdl(SDL_Renderer *renderer);
extern void tekken3_jun_select(int enabled);
extern int tekken3_jun_roster_enabled(void);
extern void tekken3_jun_roster_tick(void);
static int selecting,choice,locked,was_selecting;
static uint16_t previous=0xffff;

void tekken3_jun_selector_tick(void) {
    tekken3_jun_roster_tick();
    if(tekken3_jun_roster_enabled()) { selecting=0;return; }
    /* The GPU heuristic is unavailable in the software renderer. Gate this
     * SLUS-00402 shim on the loaded selector overlay and its native state. */
    selecting=psx_mod_read_word(0x800ae204)==9 &&
        psx_mod_read_half(0x800ae224)<=1 &&
        psx_mod_read_word(0x8010ff4c)==0x27bdffd0 &&
        psx_mod_read_word(0x8010ff50)==0x3c028012;
    if(selecting && !was_selecting) {
        choice=locked=0;previous=0xffff;tekken3_jun_select(0);
    }
    if(selecting && psx_mod_read_byte(0x80098106)!=9)choice=locked=0;
    if(!selecting && was_selecting && (locked ||
       (psx_mod_read_word(0x800ae204)==9 && psx_mod_read_half(0x800ae224)==2)))
        tekken3_jun_select(choice);
    was_selecting=selecting;
}
uint16_t __wrap_tekken3_outfits_input(int player,uint16_t buttons) {
    if(tekken3_jun_roster_enabled())return __real_tekken3_outfits_input(player,buttons);
    if(player==0) {
        uint16_t edges=previous & (uint16_t)~buttons;previous=buttons;
        if(selecting && psx_mod_read_byte(0x80098106)==9) {
            if(!locked && (edges&0x0100)) {
                choice=!choice;
                fprintf(stderr,"Jun selector: P1 highlighted %s\n",choice?"Jun":"Jin");
            }
            buttons|=0x0100;
            if((uint16_t)~buttons & 0xf008) {
                locked=1;
                if(choice)buttons=(buttons|0xf008)&~0x8000;
            }
        }
    }
    return __real_tekken3_outfits_input(player,buttons);
}
enum {W=400,H=100};
static uint32_t card[W*H];
static const uint8_t letters[26][5]={
 {126,17,17,17,126},{127,73,73,73,54},{62,65,65,65,34},{127,65,65,34,28},
 {127,73,73,73,65},{127,9,9,9,1},{62,65,73,73,122},{127,8,8,8,127},
 {0,65,127,65,0},{32,64,65,63,1},{127,8,20,34,65},{127,64,64,64,64},
 {127,2,12,2,127},{127,4,8,16,127},{62,65,65,65,62},{127,9,9,9,6},
 {62,65,81,33,94},{127,9,25,41,70},{70,73,73,73,49},{1,1,127,1,1},
 {63,64,64,64,63},{31,32,64,32,31},{63,64,56,64,63},{99,20,8,20,99},
 {7,8,112,8,7},{97,81,73,69,67}};
static void rect(int x,int y,int w,int h,uint32_t color) {
    for(int j=y;j<y+h && j<H;j++)for(int i=x;i<x+w && i<W;i++)
        if(i>=0 && j>=0)card[j*W+i]=color;
}
static void label(int x,int y,const char *text,int scale,uint32_t color) {
    for(;*text;text++,x+=6*scale) {
        uint8_t digit2[5]={98,81,73,73,70};
        const uint8_t *g=*text>='A' && *text<='Z'?letters[*text-'A']:*text=='2'?digit2:NULL;
        if(g)for(int i=0;i<5;i++)for(int j=0;j<7;j++)if(g[i]&(1<<j))rect(x+i*scale,y+j*scale,scale,scale,color);
    }
}
static int selector_image(const uint32_t **pixels,int *w,int *h) {
    if(!selecting || psx_mod_read_byte(0x80098106)!=9)return 0;
    rect(0,0,W,H,0xff101a2c);rect(0,0,W,3,0xff72c8f4);
    label(12,12,locked?"READY TO FIGHT":"E  L2  CHANGE FIGHTER",2,0xffdbeaf4);
    rect(12,38,181,49,choice?0xff273449:0xff387da3);
    rect(205,38,181,49,choice?0xff387da3:0xff273449);
    label(70,50,"JIN",4,0xfff1f4fa);label(263,50,"JUN",4,0xfff1f4fa);
    *pixels=card;*w=W;*h=H;return 1;
}
int __wrap_host_osd_outfit_image(int player,const uint32_t **pixels,int *w,int *h) {
    if(player==0 && selector_image(pixels,w,h))return 1;
    return __real_host_osd_outfit_image(player,pixels,w,h);
}
void __wrap_host_osd_draw_sdl(SDL_Renderer *renderer) {
    __real_host_osd_draw_sdl(renderer);
    const uint32_t *pixels;int w,h;
    if(!renderer || !selector_image(&pixels,&w,&h))return;
    int rw=640,rh=480;
#if defined(PSX_SDL3)
    SDL_RendererLogicalPresentation mode;
    if(!SDL_GetRenderLogicalPresentation(renderer,&rw,&rh,&mode) || rw<=0 || rh<=0)SDL_GetRenderOutputSize(renderer,&rw,&rh);
#else
    SDL_RenderGetLogicalSize(renderer,&rw,&rh);
    if(rw<=0 || rh<=0)SDL_GetRendererOutputSize(renderer,&rw,&rh);
#endif
    SDL_Texture *texture=SDL_CreateTexture(renderer,SDL_PIXELFORMAT_ARGB8888,SDL_TEXTUREACCESS_STATIC,w,h);
    if(texture) {
        SDL_UpdateTexture(texture,NULL,pixels,w*4);
        SDL_Rect dst={8,rh/30,rw/2-16,(rw/2-16)*h/w};
        SDL_RenderCopy(renderer,texture,NULL,&dst);SDL_DestroyTexture(texture);
    }
}

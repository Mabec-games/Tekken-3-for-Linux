/* Return menu-only fighter scratch without discarding a late native load. */
#ifndef TEKKEN3_JUN_UI_TEXTURE_H
#define TEKKEN3_JUN_UI_TEXTURE_H
#include <stdint.h>
#include <string.h>
#include "gpu_render.h"
typedef struct {
    uint16_t native[16*58],uploaded[16*58];
    int active;
} JunUiTexture;
static void jun_ui_texture_upload(JunUiTexture *t,unsigned x,unsigned y,const uint16_t *pixels) {
    uint16_t current[16*58];
    gr_vram_transfer_out(x,y,16,58,current);
    for(unsigned i=0;i<16*58;i++)
        if(!t->active || current[i]!=t->uploaded[i])t->native[i]=current[i];
    memcpy(t->uploaded,pixels,sizeof t->uploaded);
    t->active=1;
    gr_vram_transfer_in(x,y,16,58,pixels);
}
static void jun_ui_texture_release(JunUiTexture *t,unsigned x,unsigned y) {
    if(!t->active)return;
    uint16_t current[16*58];
    gr_vram_transfer_out(x,y,16,58,current);
    for(unsigned i=0;i<16*58;i++)
        if(current[i]==t->uploaded[i])current[i]=t->native[i];
    gr_vram_transfer_in(x,y,16,58,current);
    t->active=0;
}
#endif

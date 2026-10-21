#include <assert.h>
#include <stdio.h>
#include "../../src/tekken3_jun_ui_texture.h"
static uint16_t vram[512][1024];
void gr_vram_transfer_in(int x,int y,int w,int h,const uint16_t *p) {
    for(int row=0;row<h;row++)memcpy(&vram[y+row][x],p+row*w,w*2);
}
void gr_vram_transfer_out(int x,int y,int w,int h,uint16_t *p) {
    for(int row=0;row<h;row++)memcpy(p+row*w,&vram[y+row][x],w*2);
}
int main(void) {
    JunUiTexture selector={0},loading={0};uint16_t pixels[16*58];
    for(unsigned y=0;y<512;y++)for(unsigned x=0;x<1024;x++)vram[y][x]=1234;
    for(unsigned i=0;i<16*58;i++)pixels[i]=2000+i;
    jun_ui_texture_upload(&selector,384,160,pixels);
    jun_ui_texture_upload(&loading,400,160,pixels);
    vram[170][390]=9876; /* Native fighter upload between thumbnail frames. */
    jun_ui_texture_upload(&selector,384,160,pixels);
    vram[180][410]=8765; /* Native upload after the last thumbnail frame. */
    jun_ui_texture_release(&selector,384,160);
    jun_ui_texture_release(&loading,400,160);
    for(unsigned y=0;y<512;y++)for(unsigned x=0;x<1024;x++)
        assert(vram[y][x]==(y==170 && x==390?9876:y==180 && x==410?8765:1234));
    jun_ui_texture_release(&selector,384,160);
    jun_ui_texture_upload(&selector,384,160,pixels);
    jun_ui_texture_release(&selector,384,160);
    assert(vram[170][390]==9876);
    puts("PASS menu texture restoration, late native loads and repeated transitions");
}

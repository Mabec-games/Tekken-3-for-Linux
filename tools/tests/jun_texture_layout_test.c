#include <assert.h>
#include <stdio.h>
#include "../../src/tekken3_jun_texture_layout.h"
#include "../../src/tekken3_jun_ui_layout.h"

int main(void) {
    for(unsigned outfit=0;outfit<3;outfit++)for(unsigned player=0;player<2;player++)
        for(unsigned i=0;i<jun_texture_counts[outfit];i++) {
            const JunTextureTile *t=&jun_texture_tiles[outfit][i];
            /* Native fighter page + Jun's disabled native face-backup area. */
            assert((t->dx+t->w<=64 && t->dy+t->h<=224) ||
                   (t->dx>=64 && t->dx+t->w<=80 && t->dy+t->h<=128));
            for(unsigned k=0;k<i;k++) {
                const JunTextureTile *s=&jun_texture_tiles[outfit][k];
                assert(t->dx>=s->dx+s->w || s->dx>=t->dx+t->w ||
                       t->dy>=s->dy+s->h || s->dy>=t->dy+t->h);
            }
            unsigned ppw=4>>t->mode;
            for(unsigned y=0;y<t->h;y++)for(unsigned x=0;x<t->w;x++)
                for(unsigned sub=0;sub<ppw;sub++) {
                assert(jun_texture_tile(outfit,t->mode,t->x+x,t->y+y)==t);
                unsigned page=(t->mode<<7)|(6+t->dx/64)|(player*16);
                unsigned u=(t->dx%64+x)*ppw+sub,v=t->dy+y;
                assert(u<256 && v<256);
                assert((page&15)*64+u/ppw==384+t->dx+x);
                assert((page&16)*16+v==player*256+t->dy+y);
                assert(((page>>7)&3)==t->mode);
            }
        }
    for(unsigned loading=0;loading<2;loading++)for(unsigned ko=0;ko<2;ko++) {
        uint32_t uv=jun_ui_icon_uv(loading,ko);
        assert((ICON_PAGE&15)*64+(uv&255)/2==(loading?LOADING_ICON_X:ICON_X));
        assert(((uv>>8)&255)==ICON_Y);
        assert((uv>>22)==(ko?JUN_GREY_ROW:loading?JUN_LOADING_ROW:JUN_SELECTOR_ROW));
        assert(((uv>>16)&63)==0);
        assert((loading?LOADING_ICON_X:ICON_X)+16<=448 && ICON_Y+58<=224);
    }
    for(unsigned color=0;color<65536;color++) {
        uint16_t grey=jun_ui_grey((uint16_t)color);
        assert((grey&31)==((grey>>5)&31) && (grey&31)==((grey>>10)&31));
        assert((grey&0x8000)==(color&0x8000));
        assert((grey==0)==(color==0));
    }
    puts("PASS Jun atlas: all outfits/players/texels, no overlaps; menu UVs and KO greyscale");
    return 0;
}

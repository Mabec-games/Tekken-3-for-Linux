/* Small, transparent 2:3 portrait strip shared by GL and software renderers.
 * No fullscreen backdrop, blur, modal input or guest VRAM writes. */
#include <stdlib.h>
enum { OUTFIT_W=216, OUTFIT_H=156, PORTRAIT_W=72, PORTRAIT_H=108 };
typedef struct OutfitArt {
    char name[64];
    int loaded; /* 1 outfit art, 2 native character-portrait fallback */
    int width,height;
    uint32_t *pixels; /* Full source resolution, never a 72x108 thumbnail. */
    struct OutfitArt *next;
} OutfitArt;
static OutfitArt *outfit_art;
static int outfit_art_count;
static size_t outfit_art_pixels;
static uint32_t outfit_cards[2][OUTFIT_W*OUTFIT_H];

static unsigned outfit_u16(const unsigned char *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t outfit_u32(const unsigned char *p){return outfit_u16(p)|(uint32_t)outfit_u16(p+2)<<16;}
static void outfit_jun_portrait(OutfitArt *a,const char *base) {
    char path[1400];const char *override=getenv("TEKKEN3_JUN_ASSETS");
    if(override && override[0])snprintf(path,sizeof path,"%s/Jun-T3-ui.jui",override);
    else snprintf(path,sizeof path,"%smods/jun/Jun-T3-ui.jui",base?base:"");
    FILE *f=fopen(path,"rb");if(!f)return;
    unsigned char *data=(unsigned char*)malloc(40576);
    int valid=data && fread(data,1,40576,f)==40576 && fgetc(f)==EOF;fclose(f);
    if(valid && outfit_u32(data)==0x3149554a && outfit_u32(data+4)==1 &&
       outfit_u32(data+8)==5 && outfit_u32(data+12)==40576) {
        unsigned off=outfit_u32(data+16),length=outfit_u32(data+20);
        if(off>=56 && off<=40576 && length<=40576-off && length==544+126*252) {
            const unsigned char *tim=data+off;
            if(outfit_u32(tim)==16 && outfit_u32(tim+4)==9 &&
               outfit_u16(tim+540)==63 && outfit_u16(tim+542)==252) {
                a->pixels=(uint32_t*)malloc(PORTRAIT_W*PORTRAIT_H*4);
                if(!a->pixels){free(data);return;}
                a->width=PORTRAIT_W;a->height=PORTRAIT_H;
                for(int y=0;y<PORTRAIT_H;y++)for(int x=0;x<PORTRAIT_W;x++) {
                    int sy=y*252/PORTRAIT_H,sx=x*126/PORTRAIT_W;
                    unsigned index=tim[544+sy*126+sx]&63;
                    unsigned c=outfit_u16(tim+20+((sy/64)*64+index)*2);
                    unsigned r=(c&31)*255/31,g=((c>>5)&31)*255/31,b=((c>>10)&31)*255/31;
                    a->pixels[y*PORTRAIT_W+x]=index?0xff000000u|(r<<16)|(g<<8)|b:0xff181818;
                }
                a->loaded=2;
            }
        }
    }
    free(data);
}

static OutfitArt *outfit_load_art(const char *name) {
    for(OutfitArt *a=outfit_art;a;a=a->next)if(!strcmp(a->name,name))return a;
    if(!name[0] || outfit_art_count>=128)return NULL;
    OutfitArt *a=(OutfitArt*)calloc(1,sizeof *a);if(!a)return NULL;
    snprintf(a->name,sizeof a->name,"%s",name);
    a->next=outfit_art;outfit_art=a;outfit_art_count++;
    char path[1400];
#if defined(PSX_SDL3)
    const char *base=SDL_GetBasePath();
#else
    char *base=SDL_GetBasePath();
#endif
    snprintf(path,sizeof path,"%smods/outfit-menu/%s.rgba",base?base:"",name);
    FILE *f=fopen(path,"rb");
    if(!f && !strncmp(name,"jun-arcade-",11))outfit_jun_portrait(a,base);
#if !defined(PSX_SDL3)
    SDL_free(base);
#endif
    if(!f)return a;
    char magic[8];uint32_t w=0,h=0;
    if(fread(magic,1,8,f)!=8 || memcmp(magic,"HDRGBA01",8) ||
       fread(&w,4,1,f)!=1 || fread(&h,4,1,f)!=1 || !w || !h ||
       w>8192 || h>8192 || (uint64_t)w*h>16777216 ||
       outfit_art_pixels+(size_t)w*h>64u*1024u*1024u) {fclose(f);return a;}
    size_t size=(size_t)w*h*4;unsigned char *data=(unsigned char*)malloc(size);
    if(data && fread(data,1,size,f)==size && fgetc(f)==EOF) {
        a->pixels=(uint32_t*)data;a->width=(int)w;a->height=(int)h;
        for(size_t i=0;i<(size_t)w*h;i++) {
            unsigned char *p=data+i*4;
            uint32_t c=0xff000000u|((uint32_t)p[0]<<16)|((uint32_t)p[1]<<8)|p[2];
            a->pixels[i]=c;
        }
        outfit_art_pixels+=(size_t)w*h;a->loaded=1;data=NULL;
    }
    free(data);fclose(f);return a;
}
static void outfit_rect(uint32_t *dst,int x,int y,int w,int h,uint32_t color) {
    for(int yy=y;yy<y+h && yy<OUTFIT_H;yy++)for(int xx=x;xx<x+w && xx<OUTFIT_W;xx++)
        if(xx>=0 && yy>=0)dst[yy*OUTFIT_W+xx]=color;
}
static void outfit_text(uint32_t *dst,int x,int y,const char *text,uint32_t color) {
    for(int i=0;text[i] && x+i*8+8<=OUTFIT_W;i++) {
        unsigned char c=(unsigned char)text[i];if(c<32 || c>126)c='?';
        for(int yy=0;yy<8;yy++)for(int xx=0;xx<8;xx++)if(FONT8X8[c-32][yy]&(1u<<xx))
            outfit_rect(dst,x+i*8+xx,y+yy,1,1,color);
    }
}
void host_osd_outfit_rect(int player,int vw,int vh,int iw,int ih,int *x,int *y,int *w,int *h) {
    int margin=vh*12/720;if(margin<4)margin=4;
    /* One native bitmap pixel at 480p; keep the 8px captions legible. */
    *w=iw*vh/480;if(*w<1)*w=1;
    int maximum=vw/2-margin*2;if(maximum<1)maximum=1;
    if(*w>maximum)*w=maximum;
    *h=*w*ih/iw;
    *x=player?vw-margin-*w:margin;*y=margin;
}
int host_osd_outfit_image(int player,const uint32_t **pixels,int *w,int *h) {
    if(!HOST_OSD_VISUAL || player<0 || player>1)return 0;
    Tekken3OutfitView v=tekken3_outfits_view(player);
    if(!v.visible || !v.has_extra)return 0;
    uint32_t *dst=outfit_cards[player];memset(dst,0,sizeof outfit_cards[player]);
    uint32_t accent=player?0xff709de5:0xffe5ba57;
    char line[48];snprintf(line,sizeof line,"%s  %02d/%02d  < >: OUTFIT",v.cpu?"CPU":player?"2P":"1P",v.index+1,v.count);
    outfit_rect(dst,0,0,OUTFIT_W,12,0xe0101010);outfit_text(dst,4,2,line,accent);
    int portrait_fallback=0;
    for(int slot=0;slot<3;slot++) {
        if((v.count==1 && slot!=1) || (v.count==2 && slot==0))continue;
        int index=(v.index+v.count+slot-1)%v.count;
        const Tekken3OutfitEntry *e=tekken3_outfits_entry(v.character,index);if(!e)continue;
        int cw=slot==1?72:56,ch=cw*3/2;
        int x=slot==0?4:slot==1?72:156,y=slot==1?18:30;
        outfit_rect(dst,x-2,y-2,cw+4,ch+4,slot==1?accent:0xff555555);
        outfit_rect(dst,x,y,cw,ch,0xff181818);
        OutfitArt *a=outfit_load_art(e->art);
        if(slot==1 && a && a->loaded==2)portrait_fallback=1;
        if(a && a->loaded) {
            for(int yy=0;yy<ch;yy++)for(int xx=0;xx<cw;xx++)
                dst[(y+yy)*OUTFIT_W+x+xx]=a->pixels[(yy*a->height/ch)*a->width+xx*a->width/cw];
        } else {
            snprintf(line,sizeof line,"%02d",index+1);outfit_text(dst,x+(cw-16)/2,y+ch/2,line,accent);
        }
    }
    outfit_rect(dst,0,132,OUTFIT_W,24,0xe0101010);
    snprintf(line,sizeof line,"%.26s",v.name);outfit_text(dst,4,134,line,0xffeeeeee);
    outfit_text(dst,4,146,portrait_fallback?"X:OK O:BACK (PORTRAIT)":"X: SELECT  O: BACK",0xffbbbbbb);
    *pixels=dst;*w=OUTFIT_W;*h=OUTFIT_H;return 1;
}

/* Compose directly at the physical card size. Chrome keeps its deliberate
 * bitmap glyphs; photographs are filtered once from their full-resolution
 * source. Rebuild only on selection/size changes, not every present. */
int host_osd_outfit_image_hires(int player,const uint32_t **pixels,int width,int height) {
    static uint32_t *output[2];static int widths[2],heights[2];
    static uint32_t last_chrome[2][OUTFIT_W*OUTFIT_H];
    const uint32_t *chrome;int iw,ih;
    if(player<0 || player>1 || width<1 || height<1 || width>4096 || height>3072 ||
       !host_osd_outfit_image(player,&chrome,&iw,&ih))return 0;
    if(output[player] && widths[player]==width && heights[player]==height &&
       !memcmp(last_chrome[player],chrome,sizeof last_chrome[player])) {
        *pixels=output[player];return 1;
    }
    if(widths[player]!=width || heights[player]!=height || !output[player]) {
        uint32_t *next=(uint32_t*)realloc(output[player],(size_t)width*height*4);
        if(!next)return 0;output[player]=next;widths[player]=width;heights[player]=height;
    }
    memcpy(last_chrome[player],chrome,sizeof last_chrome[player]);
    uint32_t *dst=output[player];
    for(int y=0;y<height;y++)for(int x=0;x<width;x++)
        dst[y*width+x]=chrome[(y*ih/height)*iw+x*iw/width];
    Tekken3OutfitView v=tekken3_outfits_view(player);
    for(int slot=0;slot<3;slot++) {
        if((v.count==1 && slot!=1) || (v.count==2 && slot==0))continue;
        int index=(v.index+v.count+slot-1)%v.count;
        const Tekken3OutfitEntry *e=tekken3_outfits_entry(v.character,index);if(!e)continue;
        OutfitArt *a=outfit_load_art(e->art);if(!a || !a->loaded)continue;
        int cw=slot==1?72:56,ch=cw*3/2;
        int lx=slot==0?4:slot==1?72:156,ly=slot==1?18:30;
        int x0=(lx*width+iw-1)/iw,y0=(ly*height+ih-1)/ih;
        int x1=((lx+cw)*width+iw-1)/iw,y1=((ly+ch)*height+ih-1)/ih;
        double sw=a->width,sh=a->height;
        if(sw*3>sh*2)sw=sh*2/3;else sh=sw*3/2;
        double ox=(a->width-sw)/2,oy=(a->height-sh)/2;
        for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++) {
            double sx=ox+(x-x0+.5)*sw/(x1-x0)-.5,sy=oy+(y-y0+.5)*sh/(y1-y0)-.5;
            if(sx<0)sx=0;if(sy<0)sy=0;
            int ax=(int)sx,ay=(int)sy,bx=ax+1<a->width?ax+1:ax,by=ay+1<a->height?ay+1:ay;
            double fx=sx-ax,fy=sy-ay;uint32_t c=0xff000000u;
            for(int shift=0;shift<=16;shift+=8) {
                double top=((a->pixels[ay*a->width+ax]>>shift)&255)*(1-fx)+((a->pixels[ay*a->width+bx]>>shift)&255)*fx;
                double bottom=((a->pixels[by*a->width+ax]>>shift)&255)*(1-fx)+((a->pixels[by*a->width+bx]>>shift)&255)*fx;
                c|=(uint32_t)(top*(1-fy)+bottom*fy+.5)<<shift;
            }
            dst[y*width+x]=c;
        }
    }
    *pixels=dst;return 1;
}

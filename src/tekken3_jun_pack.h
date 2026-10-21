/* Bounds checks for source-derived v4 combat records, before guest writes. */
#ifndef TEKKEN3_JUN_PACK_H
#define TEKKEN3_JUN_PACK_H
#include <stddef.h>
#include <stdint.h>
static uint32_t jun_pack_word(const unsigned char *p) {
    return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static unsigned jun_pack_half(const unsigned char *p) {return p[0]|(unsigned)p[1]<<8;}
static int jun_pack_target(unsigned id,unsigned count) {
    return id==3 || (id>=8192 && id-8192<count);
}
static int jun_pack_validate(const unsigned char *p,size_t size) {
    if(size<32 || size>16*1024*1024 || jun_pack_word(p)!=0x314d554a ||
       jun_pack_word(p+4)!=4 || jun_pack_word(p+8)!=size)return 0;
    unsigned n=jun_pack_word(p+12),r=jun_pack_word(p+28),ro=jun_pack_word(p+20);
    if(!n || n>1024 || jun_pack_word(p+16)>=n || r!=32+n*16 ||
       r+n*56>size || ro<r+n*56 || ro>size ||
       jun_pack_word(p+24)!=4*n || 16*n+4>size-ro)return 0;
    unsigned po=ro+16*n,patterns=jun_pack_word(p+po);po+=4;
    if(patterns>1024)return 0;
    for(unsigned i=0;i<patterns;i++) {
        if(po>size-4)return 0;
        unsigned cmd=jun_pack_half(p+po),words=jun_pack_half(p+po+2);po+=4;
        if(cmd!=0xe000+i || words<3 || words>65 || words*2>size-po ||
           jun_pack_half(p+po)<1 || jun_pack_half(p+po)>60 ||
           jun_pack_half(p+po+(words-1)*2))return 0;
        po+=words*2;
    }
    if(po!=size)return 0;
    for(unsigned i=0;i<n;i++) {
        unsigned rp=r+i*56,cp=jun_pack_word(p+rp+12),clip=jun_pack_word(p+rp);
        unsigned nc=jun_pack_word(p+32+i*16+12);
        unsigned provenance=jun_pack_word(p+32+i*16+4);
        if(provenance<0x80010000 || provenance>=0x80400000 || jun_pack_word(p+32+i*16+8)!=rp ||
           jun_pack_word(p+ro+i*16)!=rp || jun_pack_word(p+ro+i*16+4)!=rp+12 ||
           jun_pack_word(p+ro+i*16+8)!=rp+28 || jun_pack_word(p+ro+i*16+12)!=rp+32 ||
           clip<r+n*56 || clip>ro-8 || (clip&3) ||
           (jun_pack_word(p+clip)&0xffffff00)!=0x4a554e00 ||
           jun_pack_word(p+clip+4)!=57 || !p[clip] || p[clip]*114u>ro-clip-8 ||
           cp<r+n*56 || cp>ro || (cp&3) || !nc || nc>4096 || nc*12>ro-cp ||
           !jun_pack_target(jun_pack_half(p+rp+16),n))return 0;
        unsigned sounds=jun_pack_word(p+rp+28),props=jun_pack_word(p+rp+32),j;
        if(sounds<r+n*56 || sounds>=ro || (sounds&3) || props<r+n*56 || props>=ro || (props&3))return 0;
        for(j=0;j<4;j++) {if(sounds+j*2>ro-2)return 0;if(jun_pack_half(p+sounds+j*2)==0xffff)break;}
        if(j==4)return 0;
        for(j=0;j<256;j++) {if(props+j*4>ro-4)return 0;if(!jun_pack_half(p+props+j*4))break;}
        if(j==256)return 0;
        for(unsigned j=0;j<4;j++)if(p[rp+40+j]>=18)return 0;
        for(unsigned j=0;j<nc;j++) {
            const unsigned char *c=p+cp+j*12;
            unsigned cmd=jun_pack_half(c);
            if(!jun_pack_target(jun_pack_half(c+6),n) || c[2] || c[3]>=83 ||
               (cmd>=0x8000 && cmd!=0xc000 && cmd!=0xc001 && cmd!=0xc002 &&
                !(cmd>=0xe000 && cmd-0xe000<patterns)))return 0;
        }
        if(jun_pack_half(p+cp+(nc-1)*12)!=0xc000)return 0;
    }
    return 1;
}
#endif

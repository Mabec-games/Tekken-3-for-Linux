#ifndef TEKKEN3_JUN_UI_LAYOUT_H
#define TEKKEN3_JUN_UI_LAYOUT_H
#include <stdint.h>
/* Menu-only fighter scratch. Page 7 contains shared effects, not free space. */
enum { ICON_X=384, LOADING_ICON_X=400, ICON_Y=160, ICON_PAGE=0x86,
       JUN_GREY_ROW=501, JUN_SELECTOR_ROW=502, JUN_LOADING_ROW=503 };
static uint16_t jun_ui_grey(uint16_t color) {
    if(!color)return 0; /* Preserve transparent entries, not just index zero. */
    unsigned grey=((color&31)*77+((color>>5)&31)*150+((color>>10)&31)*29)>>8;
    /* Keep very dark opaque entries nontransparent. Preserve the STP bit. */
    if(!grey && !(color&0x8000))grey=1;
    return (uint16_t)((color&0x8000)|grey|(grey<<5)|(grey<<10));
}
static uint32_t jun_ui_icon_uv(int loading,int knocked_out) {
    unsigned row=knocked_out?JUN_GREY_ROW:(loading?JUN_LOADING_ROW:JUN_SELECTOR_ROW);
    return (row<<22)|(ICON_Y<<8)|(loading?(LOADING_ICON_X-ICON_X)*2:0);
}
#endif

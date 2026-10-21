/* Offline SDL key-state test. Writes only the supplied disposable INI. */
#include "psx_keybinds.h"
#include "consoles/psx/psx_binds.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void same_maps(const char *path) {
    static const int order[] = {0,1,2,3,7,5,4,6,8,10,9,11,12,13,14,15,16,17,18,19,20,21,22,23};
    for (int p=0;p<2;p++)for(int b=0;b<24;b++)for(int alt=0;alt<2;alt++) {
        int actual=alt?psx_keybinds_get_button_alt(p+1,order[b]):psx_keybinds_get_button(p+1,order[b]);
        assert(rui_psx_binds_get_slot(path,p,b,alt)==actual);
    }
}
int main(int argc,char **argv) {
    assert(argc==2);
    const char *path=argv[1];
    rui_psx_binds_init(path);psx_keybinds_init(path);same_maps(path);
    assert(psx_keybinds_get_button(1,PSX_KB_UP)==SDL_SCANCODE_UP);
    assert(psx_keybinds_get_button(2,PSX_KB_UP)==SDL_SCANCODE_I);
    uint8_t keys[SDL_NUM_SCANCODES]={0};
    for(int player=1;player<=2;player++)for(int b=0;b<PSX_KB_COUNT;b++) {
        int sc=psx_keybinds_get_button(player,b);if(!sc)continue;
        keys[sc]=1;
        assert(psx_keybinds_pad_word(keys,3-player)==0xffff);
        uint8_t sticks[4]={128,128,128,128};psx_keybinds_sticks(keys,3-player,sticks);
        for(int s=0;s<4;s++)assert(sticks[s]==128);
        keys[sc]=0;
    }
    keys[SDL_SCANCODE_X]=keys[SDL_SCANCODE_KP_2]=1;
    assert(psx_keybinds_pad_word(keys,1)==0xbfff);
    assert(psx_keybinds_pad_word(keys,2)==0xdfff);
    /* Custom primary/alternate maps survive launcher/runtime reloads. */
    rui_psx_binds_set_slot(path,1,0,0,SDL_SCANCODE_F);
    rui_psx_binds_set_slot(path,1,6,1,SDL_SCANCODE_G);
    psx_keybinds_init(path);same_maps(path);
    assert(psx_keybinds_get_button(2,PSX_KB_UP)==SDL_SCANCODE_F);
    assert(psx_keybinds_get_button_alt(2,PSX_KB_CROSS)==SDL_SCANCODE_G);
    /* Deliberate unbinding must not resurrect the old shared keyboard. */
    for(int b=0;b<PSX_KB_COUNT;b++) {
        psx_keybinds_set_button(2,b,SDL_SCANCODE_UNKNOWN);
        psx_keybinds_set_button_alt(2,b,SDL_SCANCODE_UNKNOWN);
    }
    psx_keybinds_save();rui_psx_binds_init(path);psx_keybinds_init(path);same_maps(path);
    for(int b=0;b<PSX_KB_COUNT;b++)assert(!psx_keybinds_get_button(2,b));
    rui_psx_binds_reset(path,1);psx_keybinds_init(path);same_maps(path);
    assert(psx_keybinds_get_button(2,PSX_KB_UP)==SDL_SCANCODE_I);
    puts("PASS: legacy migration, separate P1/P2 keys/sticks, simultaneous input, launcher/runtime parity, custom/alternate/unbound maps and Reset");
    return 0;
}

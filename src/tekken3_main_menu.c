/* SLUS-00402: extend the native scrolling menu, not its texture atlas.
 * The working list is relocated so eleven records never overwrite the globals
 * following the original ten-record allocation. The disc remains untouched. */
#include "tekken3_main_menu.h"
#include "cpu_state.h"
#include "mod_plugins.h"

#define SCREEN 0x800ae204u
#define PHASE 0x800ae224u
#define SELECTION 0x80097f40u
#define STOCK_STATE 0x800ebfb8u
#define MENU_ENTRY 0x800db5b4u
#define QUIT_MODE 0xffu

static uint32_t state;
static int quit_requested;
extern void __real_func_80028CD4(CPUState *cpu);

int tekken3_main_menu_quit_requested(void) { return quit_requested; }

static uint32_t row(unsigned i) { return state + 16 + i * 8; }
static void copy_words(uint32_t dst, uint32_t src, unsigned bytes) {
    for (unsigned i = 0; i < bytes; i += 4)
        psx_mod_write_word(dst + i, psx_mod_read_word(src + i));
}

static int prepare(void) {
    uint32_t hi = psx_mod_read_word(0x800db5d0u);
    uint32_t lo = psx_mod_read_word(0x800db5d8u);
    if (psx_mod_read_word(MENU_ENTRY) != 0x27bdffa0u ||
        psx_mod_read_word(0x800db5ccu) != 0x24577f38u ||
        psx_mod_read_word(0x800db7dcu) != 0x2d02000au ||
        psx_mod_read_word(0x800db9f0u) != 0x90440014u)
        return 0;
    if (state && hi == (0x3c020000u | (state >> 16)) &&
        lo == (0x34560000u | (state & 65535u)))
        return 1;
    if (hi != 0x3c02800fu || lo != 0x2456bfb8u) return 0;
    /* The guest allocator supports alignment up to 4096, not 64 KiB.
     * LUI/ORI can address any allocation without signed-low-half carry. */
    if (!state) state = psx_mod_alloc_guest_memory(256, 16);
    if (!state) return 0;
    copy_words(state, STOCK_STATE, 96);
    static const char label[] = "QUIT GAME";
    for (unsigned i = 0; i < sizeof label; ++i)
        psx_mod_write_byte(state + 128 + i, (uint8_t)label[i]);
    psx_mod_write_code_word(0x800db5d0u, 0x3c020000u | (state >> 16));
    psx_mod_write_code_word(0x800db5d8u, 0x34560000u | (state & 65535u));
    return 1;
}

static int quit_index(unsigned count) {
    for (unsigned i = 0; i < count; ++i)
        if (psx_mod_read_word(row(i)) == state + 128 &&
            psx_mod_read_byte(row(i) + 4) == QUIT_MODE)
            return (int)i;
    return -1;
}

static void remove_quit(unsigned count, unsigned index) {
    unsigned selected = psx_mod_read_byte(SELECTION);
    for (unsigned i = index; i + 1 < count; ++i)
        copy_words(row(i), row(i + 1), 8);
    psx_mod_write_word(state + 4, count - 1);
    if (selected >= index) selected = selected == index ? 0 : selected - 1;
    psx_mod_write_byte(SELECTION, (uint8_t)selected);
}

int tekken3_main_menu_enter(void) {
    if (quit_requested) return 1;
    if (!psx_mod_game_started() || psx_mod_read_half(SCREEN) != 4 || !prepare())
        return 0;
    unsigned phase = psx_mod_read_half(PHASE);
    unsigned count = psx_mod_read_word(state + 4);
    if (count < 1 || count > 11) return 0;
    int index = quit_index(count);
    if (phase != 1) {
        if (index >= 0) {
            int quitting = phase == 2 && psx_mod_read_byte(SELECTION) == index;
            /* Restore native indices before dispatch/attract/reinitialization,
             * preserving remembered modes and never passing 0xff to the game. */
            remove_quit(count, (unsigned)index);
            if (quitting) { quit_requested = 1; return 1; }
        }
        return 0;
    }
    if (index >= 0 || count > 10) return 0;
    /* The first source record must really be Arcade, not an unrelated overlay
     * that happens to reuse the same RAM. Keep every other record unchanged. */
    uint32_t label = psx_mod_read_word(row(0));
    if (label < 0x80000000u || label > 0x801ffff0u) return 0;
    static const char arcade[] = "ARCADE";
    for (unsigned i = 0; i < sizeof arcade - 1; ++i)
        if (psx_mod_read_byte(label + i) != (uint8_t)arcade[i]) return 0;
    for (unsigned i = count; i > 1; --i) copy_words(row(i), row(i - 1), 8);
    psx_mod_write_word(row(1), state + 128);
    /* mode=host Quit, no controller restriction, native red font palette=2,
     * no locked/new-mode blink that could override the red. */
    psx_mod_write_word(row(1) + 4, QUIT_MODE | (2u << 16));
    psx_mod_write_word(state + 4, count + 1);
    unsigned selected = psx_mod_read_byte(SELECTION);
    if (selected >= count) selected = 0;
    else if (selected >= 1) ++selected;
    psx_mod_write_byte(SELECTION, (uint8_t)selected);
    return 0;
}

/* This compiled screen-dispatch arm hands off to the interpreted menu overlay.
 * Hook the handoff, not a generated overlay stub absent from the dispatch table.
 * Running before the overlay also makes Quit independent of VBlank timing. */
void __wrap_func_80028CD4(CPUState *cpu) {
    __real_func_80028CD4(cpu);
    if (cpu->pc == MENU_ENTRY && cpu->gpr[31] == 0x80028cdcu &&
        tekken3_main_menu_enter())
        cpu->pc = cpu->gpr[31];
}

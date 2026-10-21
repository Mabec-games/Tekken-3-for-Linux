/* Optional Anna-only replacement for the native large selector/loading TIM. */
#include "mod_plugins.h"
#include "psx_runtime.h"
#include "psx_sdl.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { ANNA_ID = 18, PORTRAIT_SIZE = 544 + 126 * 252 };
static uint8_t portrait[PORTRAIT_SIZE];
static char portrait_path[1024];
static int active, loaded;

static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void activate(void) {
    const char *base = SDL_GetBasePath();
    if (!base) return;
    int n = snprintf(portrait_path, sizeof portrait_path,
                     "%smods/anna-portrait/portrait.tim", base);
#if !defined(PSX_SDL3)
    SDL_free((void *)base);
#endif
    active = n > 0 && n < (int)sizeof portrait_path;
}

PSX_MOD_CONSTRUCTOR(register_anna_portrait) {
    (void)psx_mod_register_activation_plugin("tekken3.anna-portrait", activate);
}

static int load_portrait(void) {
    if (loaded) return loaded > 0;
    loaded = -1;
    FILE *f = fopen(portrait_path, "rb");
    if (!f) return 0;
    int ok = fread(portrait, 1, sizeof portrait, f) == sizeof portrait && fgetc(f) == EOF;
    fclose(f);
    if (!ok || le32(portrait) != 16 || le32(portrait + 4) != 9 ||
        le32(portrait + 8) != 524 || le16(portrait + 16) != 256 ||
        le16(portrait + 18) != 1 || le32(portrait + 532) != 12 + 126 * 252 ||
        le16(portrait + 540) != 63 || le16(portrait + 542) != 252) {
        fprintf(stderr, "Anna portrait: invalid native TIM; retaining stock art\n");
        return 0;
    }
    loaded = 1;
    return 1;
}

/* Called from the shared LZ decoder wrapper. Both large selector and loading
 * requests use this decoder; return-address guards avoid all other art. */
int tekken3_anna_portrait_decode(CPUState *cpu) {
    if (!active || !cpu || (cpu->pc != 0 && cpu->pc != 0x80031bfc)) return 0;
    const int selector = cpu->gpr[31] == 0x8010e574 &&
        psx_mod_read_word(cpu->gpr[16] + 0x1c) == ANNA_ID;
    const int loading = cpu->gpr[31] == 0x8004c814 && cpu->gpr[20] < 2 &&
        psx_mod_read_half(0x800add5c + cpu->gpr[20] * 2) == ANNA_ID;
    if (!selector && !loading) return 0;
    if (!load_portrait()) return 0;
    for (unsigned i = 0; i < sizeof portrait; ++i)
        psx_mod_write_byte(cpu->gpr[5] + i, portrait[i]);
    cpu->gpr[2] = sizeof portrait;
    cpu->pc = cpu->gpr[31];
    return 1;
}

#if !defined(TEKKEN3_JUN_EXPERIMENTAL)
extern void __real_func_80031BFC(CPUState *cpu);
void __wrap_func_80031BFC(CPUState *cpu) {
    if (tekken3_anna_portrait_decode(cpu)) return;
    __real_func_80031BFC(cpu);
}
#endif

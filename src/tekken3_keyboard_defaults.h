#pragma once
#include <string.h>

/* Name-based mapping keeps runtime and launcher's differently ordered tables
 * identical. Only P2's old duplicated factory layout is migrated. */
static SDL_Scancode tekken3_keyboard_default(int player, const char *name,
                                            SDL_Scancode original) {
    if (player != 1) return original; /* zero-based */
    static const struct { const char *name; SDL_Scancode key; } keys[] = {
        {"up", SDL_SCANCODE_I}, {"down", SDL_SCANCODE_K},
        {"left", SDL_SCANCODE_J}, {"right", SDL_SCANCODE_L},
        {"cross", SDL_SCANCODE_KP_1}, {"circle", SDL_SCANCODE_KP_2},
        {"square", SDL_SCANCODE_KP_4}, {"triangle", SDL_SCANCODE_KP_5},
        {"l1", SDL_SCANCODE_U}, {"r1", SDL_SCANCODE_O},
        {"l2", SDL_SCANCODE_KP_7}, {"r2", SDL_SCANCODE_KP_9},
        {"l3", SDL_SCANCODE_KP_0}, {"r3", SDL_SCANCODE_KP_PERIOD},
        {"start", SDL_SCANCODE_KP_ENTER}, {"select", SDL_SCANCODE_BACKSPACE},
        {"ls_up", SDL_SCANCODE_I}, {"ls_down", SDL_SCANCODE_K},
        {"ls_left", SDL_SCANCODE_J}, {"ls_right", SDL_SCANCODE_L}
    };
    for (unsigned i = 0; i < sizeof keys / sizeof *keys; ++i)
        if (!strcmp(name, keys[i].name)) return keys[i].key;
    return SDL_SCANCODE_UNKNOWN;
}

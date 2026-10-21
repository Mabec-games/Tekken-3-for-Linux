/* Offline menu-memory / dispatch regression. Does not boot the game. */
#include "cpu_state.h"
#include "mod_plugins.h"
#include "tekken3_main_menu.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned char ram[0x200000], extension[256];
static int started = 1, allocations, allocation_failure, yielded, interpreted;
static const uint32_t base = 0x9f038120u; /* nonzero, signed-negative low half */
static unsigned char *at(uint32_t a) {
    if (a >= base && a < base + sizeof extension) return extension + a - base;
    assert(a >= 0x80000000u && a < 0x80200000u);
    return ram + (a & 0x1fffffu);
}
uint8_t psx_mod_read_byte(uint32_t a) { return *at(a); }
uint16_t psx_mod_read_half(uint32_t a) { uint16_t v; memcpy(&v, at(a), 2); return v; }
uint32_t psx_mod_read_word(uint32_t a) { uint32_t v; memcpy(&v, at(a), 4); return v; }
void psx_mod_write_byte(uint32_t a, uint8_t v) { *at(a) = v; }
void psx_mod_write_word(uint32_t a, uint32_t v) { memcpy(at(a), &v, 4); }
void psx_mod_write_code_word(uint32_t a, uint32_t v) { psx_mod_write_word(a, v); }
int psx_mod_game_started(void) { return started; }
uint32_t psx_mod_alloc_guest_memory(uint32_t size, uint32_t align) {
    assert(size == 256 && align == 16); ++allocations;
    return allocation_failure ? 0 : base;
}
void __real_func_80028CD4(CPUState *cpu) {
    if (yielded) return;
    cpu->pc = 0x800db5b4u; cpu->gpr[31] = 0x80028cdcu;
}
extern void __wrap_func_80028CD4(CPUState *cpu);
static CPUState step(void) {
    CPUState cpu = {0}; cpu.pc = 0x80028cd4u;
    if (interpreted) {
        cpu.pc = 0x800db5b4u; cpu.gpr[31] = 0x80028cdcu;
        if (tekken3_main_menu_enter()) cpu.pc = cpu.gpr[31];
    } else __wrap_func_80028CD4(&cpu);
    return cpu;
}
static void stock_code(void) {
    psx_mod_write_word(0x800db5b4, 0x27bdffa0);
    psx_mod_write_word(0x800db5cc, 0x24577f38);
    psx_mod_write_word(0x800db5d0, 0x3c02800f);
    psx_mod_write_word(0x800db5d8, 0x2456bfb8);
    psx_mod_write_word(0x800db7dc, 0x2d02000a);
    psx_mod_write_word(0x800db9f0, 0x90440014);
}
static void native_init(unsigned count) {
    psx_mod_write_word(base, 0);
    psx_mod_write_word(base + 4, count);
    for (unsigned i = 0; i < count; ++i) {
        psx_mod_write_word(base + 16 + i*8, 0x80090000u + i*32);
        psx_mod_write_word(base + 20 + i*8, i | (6u << 16));
    }
    memcpy(at(0x80090000), "ARCADE MODE", 12);
    psx_mod_write_word(0x800ae224, 1);
}
int main(void) {
    memset(ram, 0, sizeof ram);
    memset(at(0x800ec018), 0xab, 32); /* neighbour of original allocation */
    stock_code();
    psx_mod_write_word(0x800ae204, 8); step(); assert(!allocations);
    psx_mod_write_word(0x800ae204, 4);
    started = 0; step(); assert(!allocations); started = 1;
    yielded = 1; step(); assert(!allocations); yielded = 0;
    psx_mod_write_word(0x800db9f0, 0); step(); assert(!allocations); stock_code();
    allocation_failure = 1; step(); assert(allocations == 1);
    assert(psx_mod_read_word(0x800db5d0) == 0x3c02800f);
    allocation_failure = 0; step(); assert(allocations == 2);
    assert(psx_mod_read_word(0x800db5d0) == 0x3c029f03);
    assert(psx_mod_read_word(0x800db5d8) == 0x34568120);

    for (unsigned count = 8; count <= 10; ++count) {
        for (unsigned selected = 0; selected < count; ++selected) {
            interpreted = selected & 1; /* no compiled wrapper on this path */
            native_init(count);
            unsigned char original[80]; memcpy(original, at(base + 16), count*8);
            psx_mod_write_byte(0x80097f40, (uint8_t)selected);
            step(); step(); /* no duplicate insertion */
            assert(psx_mod_read_word(base + 4) == count + 1);
            assert(psx_mod_read_byte(0x80097f40) == selected + (selected != 0));
            assert(!memcmp(at(base+16), original, 8));
            assert(!memcmp(at(base+32), original+8, (count-1)*8));
            assert(psx_mod_read_word(base+24) == base+128);
            assert(!strcmp((char*)at(base+128), "QUIT GAME"));
            assert(psx_mod_read_word(base+28) == 0x000200ff); /* red, never blink */
            psx_mod_write_word(0x800ae224, 2);
            assert(step().pc == 0x800db5b4u); /* stock mode still dispatches */
            assert(!tekken3_main_menu_quit_requested());
            assert(psx_mod_read_word(base + 4) == count);
            assert(psx_mod_read_byte(0x80097f40) == selected);
            assert(!memcmp(at(base+16), original, count*8));
        }
    }
    for (unsigned phase = 0; phase <= 3; phase += 3) {
        native_init(10); psx_mod_write_byte(0x80097f40, 9); step();
        psx_mod_write_word(0x800ae224, phase); step();
        assert(psx_mod_read_word(base+4) == 10);
        assert(psx_mod_read_byte(0x80097f40) == 9);
        assert(!tekken3_main_menu_quit_requested());
    }
    native_init(10); *at(0x80090000) = 'X'; step();
    assert(psx_mod_read_word(base+4) == 10); /* label guard */
    native_init(10); psx_mod_write_byte(0x80097f40, 255); step();
    assert(psx_mod_read_byte(0x80097f40) == 0);
    psx_mod_write_byte(0x80097f40, 1); step();
    assert(!tekken3_main_menu_quit_requested()); /* highlighting is not quitting */
    interpreted = 1; /* Quit must also intercept the dirty/cached overlay. */
    psx_mod_write_word(0x800ae224, 2);
    assert(step().pc == 0x80028cdcu); /* host Quit bypasses native mode dispatch */
    assert(tekken3_main_menu_quit_requested());
    assert(step().pc == 0x80028cdcu); /* remain stopped until host shutdown */
    assert(psx_mod_read_byte(0x80097f40) == 0);
    for (unsigned i = 0; i < 32; ++i) assert(*at(0x800ec018+i) == 0xab);
    assert(allocations == 2);
    puts("main menu: insertion, red palette, stock dispatch, re-entry, guards and Quit PASS");
}

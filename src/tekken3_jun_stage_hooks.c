/* Clean CPS entry points: correct stage ownership before loading begins,
 * never on vblank, never on a resumed continuation, and never mid-fight. */
#include "tekken3_jun_stage.h"
#include "mod_plugins.h"

extern void __real_func_800524EC(CPUState *cpu);
extern void __real_func_80036600(CPUState *cpu);

void __wrap_func_800524EC(CPUState *cpu) {
    if(!cpu->pc || cpu->pc==0x800524ec)
        tekken3_jun_stage_prepare("loading-screen");
    __real_func_800524EC(cpu);
}

void __wrap_func_80036600(CPUState *cpu) {
    if((!cpu->pc || cpu->pc==0x80036600) &&
       tekken3_jun_stage_prepare("arena-loader")) {
        /* The native cache compares pending (+8B0) against loaded (+8A0).
         * Update only the pending stage, retaining the loaded identity so
         * transitions reload and consecutive Jun rounds reuse the cache. */
        psx_mod_write_half(0x800a08b0,JUN_STAGE_ID);
    }
    __real_func_80036600(cpu);
}

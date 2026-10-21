#include "psx_runtime.h"
/* Imported drawing is a host enhancement: retire it atomically, without
 * scheduling the game at the donor ROM's program-counter addresses. */
#undef PSX_ENABLE_BLOCK_CYCLES
#define psx_slice_block(...) 0
#define psx_check_interrupts_at(...) ((void)0)
#include "jun-render.exe_full_00.c"

extern int tekken3_jun_uses_arcade_renderer(uint32_t address);
extern void __real_func_80036CAC(CPUState *cpu);
void __wrap_func_80036CAC(CPUState *cpu) {
    if ((cpu->pc==0 || cpu->pc==0x80036cac) && tekken3_jun_uses_arcade_renderer(cpu->gpr[4]))
        func_8010DC94(cpu);
    else __real_func_80036CAC(cpu);
}

extern void tekken3_jun_before_init(uint32_t model);
extern void tekken3_jun_after_init(void);
extern void __real_func_80035BC0(CPUState *cpu);
void __wrap_func_80035BC0(CPUState *cpu) {
    static uint32_t return_pc;
    if(cpu->pc==0 || cpu->pc==0x80035bc0) {
        return_pc=cpu->gpr[31];
        tekken3_jun_before_init(cpu->gpr[6]);
    }
    __real_func_80035BC0(cpu);
    if(cpu->pc==return_pc) tekken3_jun_after_init();
}

extern void __real_func_80035190(CPUState *cpu);
void __wrap_func_80035190(CPUState *cpu) {
    static uint32_t return_pc;
    if(cpu->pc==0 || cpu->pc==0x80035190) {
        return_pc=cpu->gpr[31];
        tekken3_jun_before_init(cpu->gpr[4]);
    }
    __real_func_80035190(cpu);
    if(cpu->pc==return_pc) tekken3_jun_after_init();
}

extern void __real_func_80035CE8(CPUState *cpu);
void __wrap_func_80035CE8(CPUState *cpu) {
    static uint32_t return_pc;
    if(cpu->pc==0 || cpu->pc==0x80035ce8) {
        return_pc=cpu->gpr[31];
        tekken3_jun_before_init(cpu->gpr[5]);
    }
    __real_func_80035CE8(cpu);
    if(cpu->pc==return_pc) tekken3_jun_after_init();
}

# Load ReadFudge / LDAbsorb — empirically-derived model + implementation spec

Status: **IMPLEMENTED + VALIDATED (2026-06-27).** Shipped as the shared per-instruction
R3000A load-delay interlock in `runtime/include/psx_cyc.h` (§1 base + GPR_DEPRES + DO_LDS,
+ `psx_cyc_load_*`/`psx_cyc_lwc2_read` in `memory.c`), driven by `psx_cyc_dep_res_mask`
(`runtime/include/psx_instr_cost.h`, transcribed from Beetle's per-opcode GPR_DEP/RES).
Wired into the dirty interp (`dirty_ram_interp.c`) and BOTH static emitters
(`code_generator.cpp` game path; `full_function_emitter.cpp`+`strict_translator.cpp` BIOS
path). Loads route value reads through the UNCHARGED `psx_read_*` (cpu->read_* rewired in
main.cpp); the data-access cost is charged once, inside the interlock. VALIDATED against the
Beetle oracle: ruler #2 `load2` native +10 → **+11** == Beetle (all other components
unchanged + matching); ruler #1 [0x80001C5C→0x80001CA4] 54 → **56** == Beetle steady-state
(residual 84/77 spikes = I-cache cold refill, the separate P2 axis); Tomba 2 boots to the
intro FMV (no regression). The `(ReadFudge>>4)&2` fudge, the region(RAM +3)+completion(+2)
LDAbsorb give-back, and scratchpad +0 are all modeled per below.

FOLLOW-UP — **DONE + VALIDATED (2026-06-27, same session).** GTE-read (MFC2/CFC2) +
MFC0 LDAbsorb give-back arming, and the muldiv-stall give-back consumption / off-by-one
(Beetle cpu.cpp:1332-1341 / 1723-1736). Shipped: `psx_gte_read` (stall + arm give-back) for
MFC2/CFC2 in both emitters + interp (MTC2/CTC2 stay `psx_gte_stall`); MFC0 arms
ld_absorb=0/ld_which_t=rt; `psx_muldiv_stall` now consumes read_absorb during the stall +
the muldiv_ts_done-1 off-by-one. **All 12 ruler #2 loops now == Beetle at steady state**:
the 4 divergences closed (gte_rtps 18→14, gte_nclip 11→7, gte_read_use 19→14, ld_div 45→49)
and the 8 prior matches held; ruler #1 delta 0; Tomba 2 FMV plays (jungle scene, no
regression). The original FOLLOW-UP text + the Δ-gate table below is retained for the record.

Original FOLLOW-UP note (CONFIRMED divergences — ACCURACY axis-2): GTE-read (MFC2/CFC2) +
MFC0 LDAbsorb give-back arming, and the muldiv-stall give-back consumption / off-by-one
(Beetle cpu.cpp:1332-1338 / 1723-1736). **Δ-GATED** by new ruler #2 probe loops, measured at
STEADY STATE (Beetle must run long enough — its warm-up window reports the no-give-back
value, which is why the handoff mis-recorded gte_rtps as "+15 EXACT"; the true steady
Beetle value is +11). Steady-state native(no give-back) vs Beetle(give-back):

| loop          | native | Beetle | gap | divergence source                        |
|---------------|--------|--------|-----|------------------------------------------|
| gte_rtps      | 18     | **14** | +4  | MFC2 give-back (LDAbsorb=gte_ts_done-ts)  |
| gte_nclip     | 11     | **7**  | +4  | MFC2 give-back                            |
| gte_read_use  | 19     | **14** | +5  | MFC2 give-back (then dependent use)       |
| ld_div        | 45     | **49** | −4  | muldiv stall must CONSUME the lw give-back|

Implementation: MFC2/CFC2 — after §1+DO_LDS, stall to gte_ts_done AND set
ld_absorb = (gte_ts_done - now), ld_which_t = rt (replace psx_gte_stall on READS only;
MTC2/CTC2 stay stall-only). MFC0 — arm ld_which_t=rt, ld_absorb=0. muldiv stall (MFLO/MFHI)
— while stalling to muldiv_ts_done, decrement read_absorb[read_absorb_which] per cycle, and
the muldiv_ts_done-1 off-by-one decrement (Beetle cpu.cpp:1723-1736). Re-validate the FULL
12-loop suite at steady state (the 8 passing components must stay matched).
All-CPU-load + alu + div + mult components MATCH at steady state — COMMIT 1 is solid.

---
ORIGINAL SPEC (model derivation) follows.

This is
the last unmodeled piece of the load path — the residual on BOTH rulers
(ruler #1 native 54 vs Beetle 56; ruler #2 `load2` native +10 vs Beetle +11). It
is the R3000A load-delay pipeline interlock (Beetle `ReadFudge`/`ReadAbsorb[]`/
`LDAbsorb`/`LDWhich`). Derived by measuring Beetle's PER-INSTRUCTION cost via
adjacent-PC region cyc_watch (Beetle observes per-instruction; the native compiled
emitter observes only at block leaders, so native per-insn is not observable — Beetle
is the per-instruction oracle here).

## Empirical per-instruction costs (Beetle oracle, ruler #2 loops)

| loop      | per-instruction Δ (cycles)                  | per-iter |
|-----------|---------------------------------------------|----------|
| baseline  | addiu **1**, bne **1**, nop **1**           | 3        |
| load      | lw **7**, addiu **1**, bne **0**, nop **0** | 8 (+5)   |
| load2     | lw1 **7**, lw2 **6**, addiu **1**, bne **0**, nop **0** | 14 (+11) |

Reading these:
- **1st lw = 7**: fudge 2 + region 3 + completion 2. The +2 fudge appears because the
  instruction before it (nop / branch) committed NO load.
- **2nd lw = 6**: fudge **0** (prev instruction was a load) + region 3 + completion 2
  + **its own §1 base +1 (NOT absorbed)**. = 0+3+2+1.
- **delay-slot instruction (addiu) stays 1**: its §1 runs BEFORE its own DO_LDS sets
  `ReadAbsorb[loaded]`, so it cannot absorb the load it follows.
- **bne, nop = 0**: absorbed from the load's `LDAbsorb` give-back.

## The model (Beetle cpu.cpp, confirmed by the table above)

Per instruction, in order:
1. **fetch** (§2, separate axis — I-cache; 0 for cached-RAM steady state).
2. **§1 base** (cpu.cpp:795-798): `if (ReadAbsorb[ReadAbsorbWhich]) ReadAbsorb[ReadAbsorbWhich]--; else timestamp++;`
   — `ReadAbsorbWhich` = the GPR the most-recently-committed load wrote.
3. **GPR_DEP/RES** (cpu.cpp:702-705): for each source/dest reg of this instruction,
   `ReadAbsorb[reg]=0` (save/restore `ReadAbsorb[0]`). This ends the give-back when the
   loaded value is actually used (load-use hazard).
4. **execute**; a load (LW/LH/.../LWC2) runs ReadMemory (§3, cpu.cpp:364-451):
   - `timestamp += (ReadFudge>>4)&2` — the **fudge**. NOTE: `ReadFudge` holds the last
     load's dest reg (0-31) OR **0x20** when the previous instruction committed no load.
     `(x>>4)&2` is **0 for any reg 0-31** and **2 only for 0x20**. So fudge = **+2 iff the
     previous instruction committed no pending load**, else 0. (This is the non-obvious
     part — it is NOT per-register.)
   - region wait-state (main RAM = 3; scratchpad 0x1F800000-0x1F8003FF = 0 early-return;
     other regions differ), then `+2` (CPU load) or `+1` (LWC2/GTE load).
   - `LDAbsorb = lts - timestamp` = **region + completion (EXCLUDES fudge)** = 5 for main RAM.
5. **DO_LDS** (cpu.cpp:800), at the END of the handler: commits the PREVIOUS instruction's
   pending load: `GPR[LDWhich]=LDValue; ReadAbsorb[LDWhich]=LDAbsorb; ReadFudge=LDWhich;
   ReadAbsorbWhich |= LDWhich&0x1F; LDWhich=0x20;`. When `LDWhich==0x20` (no pending),
   `ReadFudge` becomes 0x20 → next load gets +2 fudge.

Stores are posted (+0, already modeled). Scratchpad loads are +0 (early-return, LDAbsorb=0).

## Why our current model is off

Current: flat `+1` base per instruction (PSX_CODEGEN_CYCLE_PER_INSN) + `memory.c`
charges a flat region wait-state (PSX_RAM_READ_WAIT_CYCLES=4) per RAM read. This
captures region+completion≈5 for an isolated load (matches `load`=+5) but MISSES:
(a) the **fudge** (+2 on a load whose predecessor wasn't a load → `load2` 2nd lw),
(b) the **absorb give-back** (following instructions going free), and
(c) scratchpad=+0. (a) and (b) happen to partially cancel on the `load` loop (why
single-load already matches) but not on `load2` / dependent-use sequences.

## Implementation plan (pervasive — a focused next task)

1. CPUState (append at end): `ReadFudge`, `ReadAbsorb[33]`, `ReadAbsorbWhich`,
   `LDWhich`, `LDAbsorb`. (`LDValue`/value-commit already handled by the existing
   load-delay-slot correctness path — only the TIMING state is new.)
2. `psx_cycles.c`: helpers for §1 (`psx_cyc_base`), the load cost+fudge+LDAbsorb arm,
   and DO_LDS timing-commit. region wait-state stays address-keyed in `memory.c` but
   must feed LDAbsorb (region+completion), and set fudge from ReadFudge.
3. Both emitters (code_generator.cpp, strict_translator.cpp) + dirty interp: replace the
   flat per-instruction `+1` with the §1 call, and emit `GPR_DEP/RES` zeroing for each
   instruction's source/dest registers (the pervasive part — every opcode passes its
   regs). Loads arm LDWhich/LDAbsorb; the next instruction's timing-DO_LDS commits.
4. Interaction with muldiv/GTE stalls: those use `*_ts_done` deadlines independent of
   ReadAbsorb — keep them; just ensure the §1 base replacement doesn't double-count.
5. **Validate** via the existing ruler-loop anchors (observable at loop tops): `baseline`=3,
   `load`=8, `load2`=14 must match Beetle EXACTLY; ruler #1 [c5c→ca4] should reach 56;
   FMV no-regression. Add a load-then-dependent-use loop to ruler #2 to pin the
   GPR_DEP give-back termination.

Risk: pervasive per-instruction emit change to the cost model — do it on a clean tree
with full budget, validate one ruler loop at a time.

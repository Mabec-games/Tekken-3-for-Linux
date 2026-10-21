# Precise interrupt-take-point fix — cycle-budgeted precise event slicing

Status: IN PROGRESS (Phase 1). Branch wt/tomba2. Root cause = interrupt
take-point granularity (compiled blocks take IRQs only at block edges; HW +
the dirty-RAM interpreter take them at the exact instruction). Oracle-confirmed
(Beetle exc_ring caught HW take at epc=0x8008593C, mid-block). Validated with
ChatGPT (Recomp project, "PSX IRQ Debugging" chat) — design below is the
agreed plan.

## Already in place (committed tip 8ab24c5, live)
- ABI v8 overlay callback `check_interrupts_at(cpu, resume_pc)`.
- Emitter emits `psx_check_interrupts_at(cpu, <resume_pc>)` at block EXITS
  (jr/jalr/branch/j/jal) — currently a runtime SHIM forwarding to
  `psx_check_interrupts` (interrupts.c). Block-LEADER `psx_check_interrupts`
  was removed.
- Per-block cycle accounting: `psx_advance_cycles(bcyc)` at each block leader
  (PSX_ENABLE_BLOCK_CYCLES=1). Fans out to sio/cdrom/dma/timers/interrupts
  _advance() in psx_cycles.c.
- Sanctioned dirty-RAM interpreter (dirty_ram_interp.c, complete MIPS+GTE+COP0)
  ALREADY takes IRQs at exact instructions, charges 1 cyc/insn, and is proven
  CYCLE+STATE identical to compiled for frames 1..1823. It is a trusted retire
  engine, not a fallback.

## The fix (3 mechanisms)

### 1. cycles_to_next_event(i_mask)  [Task #2 — additive, no behavior change]
Single source of truth = min over peripherals of the distance (guest cycles)
to the next DELIVERABLE interrupt raise (NOT merely the next i_stat raise).
"Deliverable" = the source's IRQ bit is unmasked in i_mask AND mode-enabled.
Each peripheral exposes its own `<p>_cycles_to_irq(uint32_t i_mask)` returning
UINT32_MAX if none:
- VBLANK: interrupts.c owns cycles_since_vblank -> VBLANK_CYCLES - cycles_since_vblank.
- timers: per timer with IRQ_TARGET/IRQ_OVERFLOW enabled AND bit in i_mask;
  ticks to next target/overflow * clk-divisor - timer_frac. Divisors: sysclk=1,
  timer1 hblank=2146, timer2 sysclk/8=8, timer0 dotclock=5.
- cdrom: min active countdown that raises bit2 (cdrom_irq_present_delay when a
  response is armed; pending.delay; read_delay) gated on bit2 in i_mask.
- dma: per active async channel, cycles to completion (remaining_words *
  CYCLES_PER_WORD - cycles_accum; advance_delayed_complete countdowns) gated on
  bit3 in i_mask + DICR enable.
- sio: sio_irq_countdown when armed + IRQ enabled, gated on bit7 in i_mask.
Conservative rule: when unsure, round DOWN (smaller distance => slice more =>
safe). Over-estimating the distance is the only dangerous direction.

### 2. Two-tier block execution  [Task #3]
At each block leader (emitter), BEFORE the body:
    fast-safe iff:  !irq_visible_now()
                 && cycles_to_next_event() > bcyc
                 && !block_has_irq_visibility_side_effects   (static, see below)
  fast-safe  -> psx_advance_cycles(bcyc); run compiled body (current path).
  else       -> cpu->pc = block_addr; return; and the dispatch loop enters
                PRECISE INTERPRETER MODE from block_addr.
`block_has_irq_visibility_side_effects` is a STATIC per-block emitter flag set
when the block writes I_STAT / I_MASK / COP0 Status/Cause / IRQ-source MMIO, or
contains mtc0 / rfe. Such blocks can change deliverability mid-block with no new
hardware event due, so they must take the precise path (or guard internally).

### 3. Precise interpreter mode  [Task #3]
Run the EXISTING dirty-RAM interpreter from cpu->pc. It CONTINUES ACROSS
fallthroughs, branches, jumps, jal/jalr, returns, compiled-function boundaries,
and dirty-RAM boundaries — owned by the EVENT DEADLINE, not the function
boundary (avoids the re-entrancy problem). Exit precise mode when ONE of:
  - the IRQ is taken (exact-instruction exception entry), OR
  - the event deadline passed and no IRQ is pending+enabled, OR
  - execution reaches a safe dispatch boundary where the next compiled block is
    provably fast-safe (cycles_to_next_event > that block's bcyc, no side effects).

### Exact exception entry  [Task #4 — interp already does most of this]
EPC = restart PC (branch PC if in a branch-delay slot; set Cause.BD), CP0
Status/Cause exact, load-delay carried into the handler. Do NOT manufacture a
block-entry EPC. Every IRQ-affecting write is an unconditional safe-point that
recomputes pending IRQ before the next instruction.

## Decisions locked with ChatGPT
- Reuse the interpreter as the precise sliced executor: SOUND and the better
  first implementation (1823-frame parity proves equivalence). Generated
  "precise sidecars" are only a later perf optimization, never a correctness need.
- Slice window owned by the event deadline; keep interpreting through callees.
- "check IRQ at block edge with EPC=block-entry/exit" is WRONG (fake EPCs) — the
  committed block-exit check is fine only as the fast path's own edge check;
  correctness comes from the leader slice-guard + precise mode.

## Task #3 implementation notes (architecture mapped 2026-06-26)

- `psx_dispatch_impl` (generated SCPH1001_dispatch.c — DO NOT edit) is a tail-call
  trampoline; `psx_check_interrupts` runs only when the OUTERMOST dispatch returns.
- `dirty_ram_dispatch` / `_inner` (hand-written, editable) interpret a block via a
  loop over `exec_one()`, but for CLEAN game-text pages `_inner` routes back to
  `psx_dispatch_game_compiled` (compiled). Interrupts are pumped only every ~4096
  insns (outer pump + local-flow inner pump). So this path is NOT per-instruction
  precise — it's 4096-insn granular. The "interp reference" matching HW well enough
  to reach the FMV is that 4096-granularity landing somewhere in the tight debounce
  loop; Beetle/HW take at the EXACT instruction. Precise-mode must be FINER than the
  existing interp: check the deliverable-IRQ condition after EACH instruction inside
  the slice window (the window is short, bounded by cycles_to_next_event, so the
  per-insn cost is paid only when an event is imminent).
- `exec_one()` is the reusable per-instruction primitive AND it nests jal/jalr inline
  via `psx_dispatch_call` (runs the callee COMPILED). 

### Design decision — RESOLVED via ChatGPT: option (b)
Precise-mode CONTINUES THROUGH statically-compiled callees, owned by the event
deadline, NOT the call boundary. Option (a) [surface at the call, re-arm at the
callee's first leader] was REJECTED: if the IRQ is actually due deeper inside the
callee, taking it at the callee's first block leader is a FAKE take-point. Hard
invariant: "native compiled code is never entered recursively from precise mode —
while precise mode is active, it IGNORES native availability."

Clean implementation (maps onto the existing interp with minimal change):
- A global `g_precise_mode`. While set, `interp_enter_compiled()` (dirty_ram_interp.c)
  RETURNS 0 (declines) — the existing jal/jalr handler already treats 0 as "interpret
  locally," so calls step INTO the callee per-instruction instead of running it
  compiled. This realizes "ignore native availability" with no new call machinery.
- Precise loop = exec_one() + psx_advance_cycles(1) + a PER-INSTRUCTION deliverable-IRQ
  check (FINER than the existing interp's ~4096-insn pump, which is only a parity
  comparator, not HW-precise). On a deliverable IRQ: set g_dirty_safe_resume_pc to the
  committed next PC and call psx_check_interrupts (takes at the exact instruction).
- EXIT not at "event fired" but when: IRQ taken (pc now in the handler/vector), OR the
  deadline passed AND no IRQ is pending+enabled at the next instruction boundary, OR a
  safe dispatch boundary where the next compiled block is provably fast-safe. Then set
  cpu->pc to the resume PC and return to the trampoline (which tail-dispatches compiled).
- Re-entrancy is structurally impossible: precise-mode never enters compiled, so the
  emitted block-leader guard is never re-hit during a slice window.

### Emitter hook
At each block leader, BEFORE psx_advance_cycles(bcyc), emit (full_function_emitter.cpp):
    if (psx_block_needs_slice(bcyc, <side_effect_flag>)) { cpu->pc = <block_addr>; return; }
`psx_block_needs_slice` (runtime): returns (cycles_to_next_event() <= bcyc) ||
side_effect_flag || <irq already visible>. On true, the compiled block returns with
cpu->pc=block_addr and a global `g_psx_slice_request=1`; the dispatch path runs
precise-mode from block_addr instead of re-dispatching compiled (else infinite loop
re-hitting the same leader). The cleanest seam that avoids editing generated
dispatch: have `psx_block_needs_slice` itself run precise-mode inline and set cpu->pc
to the safe resume PC, then the block `return`s and the trampoline tail-dispatches
the safe PC compiled. (Decide seam during impl; keep generated-code change to the
single emitted guard line.)

## Implementation status (2026-06-26 evening) — Task #4 ROOT-CAUSED (handoff hypothesis CORRECTED)

The prior handoff's Task #4 hypothesis ("nested psx_check_interrupts leaves pc=0
because of setjmp/dispatch-depth/cooldown/VBlank-pacing") was REFUTED by state
evidence. The real root cause is the RESUME PC, not the take machinery.

### Evidence (slice-trace + always-on rings, port 4500)
- Reproduced the deterministic pc=0 with the current build. Added slice-trace
  globals (g_slice_last_block/_first_pc/_first_insn/_committed/_istat/_imask/_sr/
  _entry_deliverable) surfaced in freeze_check.
- The slice fires at game block 0x80017FEC (NOT 0x8001A2F4 — the earlier
  event-ring read of "resume=0xB0" was a DIFFERENT, earlier delivery; red herring).
  first_insn = 0x8FA20010 (`lw v0,0x10(sp)`), committed = 0x80017FF0.
- precise_irq_deliverable was TRUE at slice entry; the loop ran ONE instruction then
  took the IRQ with resume = 0x80017FF0 — a MID-FUNCTION clean-game-text PC.
- ROOT CAUSE: psx_dispatch_game_compiled is a switch over function ENTRIES (+ CPS
  call-return continuations). A mid-function clean-text PC is NOT in it -> returns 0;
  the page is not dirty -> dirty_ram_dispatch_inner returns 0 (line 1685-1731) ->
  top-level reads pc as 0 ("execution completed"). NOT a take-machinery bug.
  Tested+REFUTED: gating cooldown + VBlank-pacing on g_precise_mode did NOT fix it.
- A/B isolation (PSX_PRECISE_SLICE env toggle, now permanent in psx_slice_block):
  slice-OFF boots clean past frame 798; slice-ON dies. The slice is the sole cause.

### The fix (ChatGPT-validated, "PSX Static Recompiler Debug" thread 2026-06-26)
DECISIVE RECOMMENDATION: make EVERY basic-block leader a re-enterable CPS
continuation. That is the correct class fix for exact-instruction IRQs in a static
recompiler. Do NOT route clean compiled text through the dirty-RAM interpreter
(reintroduces the 4096-pump/cap/deadlock class). Invariant:
  function entry != only valid native entry;
  basic-block leader = valid intra-function continuation entry.
- Global dispatch maps each block leader -> its OWNING function with cpu->pc set
  (`case L: cpu->pc=L; func_OWNER(cpu); return 1;`), NOT a new function entry —
  preserves "never seed an interior address as a function entry" (truncation rule).
- Each function's existing `if(cpu->pc!=0) switch(_cont){case X: goto block_X;}`
  is extended to ALL block leaders (today only CPS call-returns).
- precise-mode interprets ONLY to the next post-transfer boundary (a block leader),
  then hands back — bounded to "remaining insns in current block + delay/transfer",
  NOT "until some future call-return". Fixes the delay-loop deadlock
  (do{[sp+16]--;}while(!=-1) in func_80017FC4, leaders 0x80017FEC/..34 not entries).
- Block-leader set must include: branch/jump targets, post-delay fallthrough
  (branch_pc+8), call-return PCs, statically-known computed-jump targets.
- Pitfall (live-in safety): satisfied — guest regs are canonical in cpu->gpr[]
  (generated C uses cpu->gpr[] directly; only block-local _bc_* temps are C locals).
- FAIL CLOSED, never silent pc=0: if the slice cap trips before reaching a
  dispatchable PC -> fatal diagnostic precise_slice_failed_to_reach_block_boundary
  {pc,start,last,count,owner}. If a clean-text transfer target is not a known leader
  (indirect/jump-table discovery gap) -> log clean_text_undispatchable_pc + fail
  closed. pc=0 must mean only a real guest pc=0 / explicit termination.

PROGRESS so far: runtime psx_run_precise restructured (irq_taken-once + every exit
gated on precise_pc_dispatchable, which calls the new generator predicate
psx_game_is_function_entry). With ONLY function-entries+CPS-returns dispatchable,
boot advanced frame 798->800 and 1 slice -> 432 slices, then deadlocks on the
func_80017FC4 delay loop (its leaders aren't entries). NEXT: emit ALL block leaders
as continuations in the generator (full_function_emitter.cpp + main_psx.cpp), then
the delay-loop leaders become dispatchable and the slice hands back within one block.

## Validation  [Task #5]
- Beetle exc_ring oracle: native exception-entry record (cycle, last/next PC,
  EPC, BD, Status/Cause, I_STAT/I_MASK, pending-load) must match interp + Beetle
  at the f1823->1824 VBLANK.
- Regen + screenshot-smoke ALL titles (BIOS, Tomba 1, MMX6, Ape, Tomba 2).
- Delete Tomba2 overlay_native_block; native must still reach the FMV/title.
- Only then: pin bump (user-gated).

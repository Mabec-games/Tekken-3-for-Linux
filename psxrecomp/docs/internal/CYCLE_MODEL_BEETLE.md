# R3000A Cycle Model — extracted from the Beetle/Mednafen oracle

Companion to FAITHFUL_TIMING_PLAN.md (§3b/§3c) and ACCURACY_BURNDOWN.md (axis 2).
This is the **ground-truth model** our shared `psx_instr_base_cycles` (+ the
memory-path wait-state charger) must reproduce. Every number here is transcribed
**verbatim from the in-tree oracle** `psxrecomp/beetle-psx/mednafen/psx/cpu.cpp`
(main checkout) with the exact line cited, cross-referenced against nocash psx-spx.
These are HARDWARE FACTS (cycle counts), not GPL-protected expression — we
re-implement the model in our own code, we do not paste Beetle's code.

> Method (CLAUDE.md §15, Rule -1): a number here is only trusted once it has been
> VALIDATED at runtime via the cyc_watch Δ gate (native==Beetle==analytic on a
> clean ruler). Until then it is a transcription HYPOTHESIS.

---

## The accumulator

Beetle accumulates a single per-slice `pscpu_timestamp_t timestamp`. The cyc_watch
oracle samples it **at block entry, BEFORE the anchor instruction executes**
(cpu.cpp:748-749), identical to the native capture point. So the Δ between two
consecutive same-anchor hits (or a two-anchor A→B region) is the total guest
cycles charged for exactly the code between them. THIS is what we match.

## 1. Per-instruction base cost  (cpu.cpp:795-798)

```
if (ReadAbsorb[ReadAbsorbWhich]) ReadAbsorb[ReadAbsorbWhich]--;   // absorb a pending load-delay
else                             timestamp++;                     // otherwise +1
```

- **Base = +1 per retired instruction.** This is the Stage-1 identity model we
  already have.
- BUT a pending **load-delay absorb** (see §3) is consumed *instead* of charging
  the +1. So an instruction that reads a just-loaded register can be effectively
  free. This is the pipeline overlap; it makes naive "loads cost +2" an
  OVER-count when the result is consumed immediately.

## 2. Instruction fetch / I-cache  (cpu.cpp:534-601, ReadInstruction)

Charged into `timestamp` at fetch time, BEFORE the base +1. Depends on the
address region and I-cache state:

- **I-cache HIT** (`ICache[idx].TV == address`): **+0**. (Steady-state of any loop
  living in cached RAM after its first pass.)
- **Cache-DISABLED** — `address >= 0xA0000000` (KSEG1) or BIU bit 0x800 clear:
  **+4 every fetch** (cpu.cpp:550; "approximate best-case cache-disabled time,
  can be 5 in some nop runs"). **BIOS ROM at 0xBFC00000 is KSEG1 → +4/fetch
  always.** Game/kernel code relocated to KSEG0/KUSEG RAM is cached.
- **Cache-ENABLED MISS** (cached RAM, line tag mismatch): **+3** (cpu.cpp:565)
  then **+1 per word refilled** from the missing word index to the end of the
  4-word (16-byte) line (fall-through switch cpu.cpp:568-595). So a miss on:
  - word 0 of the line → +3 +4 = **+7**, then next 3 fetches in that line HIT (+0)
  - word 1 → +3 +3 = +6 ; word 2 → +5 ; word 3 → +4.
  Average over a long straight cached run ≈ (7+0+0+0)/4 ≈ **+1.75/instr**; a tight
  loop fully resident in cache after warm-up → **+0/instr**.

Recompiler consequence: fetch is a per-PC/region constant we can fold into the
per-block charge (cache-enabled steady state for RAM; flat +4 for KSEG1 ROM
blocks). The cached-miss warm-up is a per-line transient — model the steady state,
account the warm-up only where a region is entered cold.

## 3. Data loads — ReadMemory  (cpu.cpp:364-451)

For a load instruction (LB/LH/LWL/LW/LBU/LHU/LWR; LWC2 = LWC timing):

1. **Scratchpad** `0x1F800000..0x1F8003FF` (cpu.cpp:414-422): early return,
   `LDAbsorb=0`, **+0**. Scratchpad is the D-cache — fast, no stall.
2. Otherwise: `timestamp += (ReadFudge>>4)&2` (cpu.cpp:424) — a **+0 or +2
   read-after-load "fudge"** (penalty when the previous op set ReadFudge).
3. Region wait-state: `PSX_MemRead*(lts, address)` advances `lts` by the bus
   wait-state for that region (main RAM, BIOS ROM, MMIO each differ — see the bus/
   memory map; main RAM is the fast case).
4. `lts += (LWC_timing ? 1 : 2)` (cpu.cpp:442-445) — the load completion cost
   (**+2** normal CPU load, **+1** LWC2/GTE load).
5. `LDAbsorb = lts - timestamp` (cpu.cpp:447) — the whole data-access cost becomes
   the **load-delay absorb**: it is handed to `ReadAbsorb[rt]` in DO_LDS
   (cpu.cpp:800), so the next instruction(s) that read `rt` consume it via §1
   instead of charging their own +1. Net: a load costs (fudge + region + 2), but up
   to that many following dependent-instruction +1's are absorbed back.

> Our current `psx_instr_base_cycles` charges a flat +3 for CPU loads (1 base + 2),
> +2 for LWC2. That captures step 4 only — it MISSES scratchpad=+0 (over-counts),
> the region wait-state (under-counts non-RAM), the ReadFudge (+0/2), and the
> absorb give-back (over-counts when the load result is used immediately). Those
> are the next Δ-gated refinements; some push native UP, some DOWN.

## 4. Stores — WriteMemory  (cpu.cpp:453+)

Stores are **POSTED**: WriteMemory adds **no CPU stall** to `timestamp` (scratchpad
and RAM both just write). So a store = the +1 base only. (Bus-level write latency
is hidden behind the write buffer.)

## 5. Mult/Div latency  (cpu.cpp: MULT_Tab24 ~L101, muldiv_ts_done ~L154, 724/758/764)

MULT/DIV set a **completion timestamp** `muldiv_ts_done`; a later **MFHI/MFLO
stalls** until then (does not block other instructions). Documented latencies:
- **MULT/MULTU**: ~6–13 cycles by operand magnitude (`MULT_Tab24` lookup on the
  leading bits of the multiplier).
- **DIV/DIVU**: ~**36** cycles (fixed).
Model: a small latency attached to the mult/div op + a stall-on-read at MFHI/MFLO
if the consumer arrives before `muldiv_ts_done`. (In straight code with enough
spacing the stall is hidden.)

## 6. GTE / COP2 per-command  (gte.cpp GTE_Instruction ~L1713)

Each COP2 op returns its own cycle count; GTE sets `gte_ts_done` and a COP2 read
stalls until then (cpu.cpp:1334/1369 set LDAbsorb from `gte_ts_done`). Well-known
table (psx-spx; verify each against the gte.cpp op-fn return before trusting):
RTPS=15 RTPT=23 MVMVA=8 SQR=5 OP=6 AVSZ3=5 AVSZ4=6 NCLIP=8 NCDS=19 NCDT=44
NCCS=17 NCCT=39 NCS=14 NCT=30 CC=11 CDP=13 DPCS=8 DPCT=17 DCPL=8 INTPL=8
GPF=5 GPL=5.

## 7. Branches / jumps

No extra base cost beyond §1 (+1) and the fetch of the delay-slot instruction.
The R3000 has no branch-likely; the delay slot always executes and is charged its
own +1 (this is the −8 delay-slot-ownership class already fixed in our emitter).
Exception entry has its own path (Exception()).

---

## What our model currently has vs. this

| Component        | Beetle (this doc)                    | Our psx_instr_base_cycles      | Gap |
|------------------|--------------------------------------|--------------------------------|-----|
| base/instr       | +1 (minus absorb)                    | +1                             | absorb give-back not modeled |
| CPU load         | fudge + region + 2, becomes absorb   | flat +3                        | scratchpad/region/fudge/absorb |
| LWC2 load        | region + 1, becomes absorb           | +2                             | same |
| store            | +0 (posted)                          | +1 (the base) — OK             | — |
| fetch / I-cache  | +0 hit / +4 KSEG1 / +3+refill miss   | not modeled (0)                | the big RAM-cached vs ROM lever |
| mult/div         | mult 6-13, div 36, stall-on-read     | not modeled (+1)               | yes |
| GTE per-command  | per-op table 5..44                   | not modeled (+1)               | yes |

Implement one row at a time, each Δ-gated on a clean ruler (BIOS leaf fn +
HW test ROM), each verified native==Beetle==analytic, FMV-no-regression, commit.

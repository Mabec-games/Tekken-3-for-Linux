# Native-vs-interp first-divergence tooling

**Dev tooling only — never shipped.** The Python scripts here drive debug-server
commands that are all `PSX_NO_DEBUG_TOOLS`-stripped from release builds, so none
of this reaches production. It exists so we never have to re-invent the
first-divergence workflow that root-caused the Tomba 2 logo→FMV stall.

## The idea

A recomp title run two ways — **native** (compiled BIOS + compiled overlays +
the sanctioned dirty-RAM interp) vs the **interp reference**
(`PSX_OVERLAY_NATIVE_OFF=1`, full dirty-interp from boot) — is the *same
deterministic program*. They must emit an identical sequence of guest
side-effects until a codegen or timing bug forks them. Find that fork in three
ever-narrowing layers. Ring-buffer-first: never arm-then-time; the fingerprint
ring is always-on, you query it after the fact.

### Layer 1 — which FRAME forks (always-on ring, O(1))
`frame_fingerprint` keeps cumulative rolling hashes, snapshotted per guest
frame, over guest writes: `wr` (main-RAM addr/val), `pc` (store-PC path),
`mmio` (device-register writes), `sp` (scratchpad writes — separate so it
classifies instead of hiding), plus `cyc` (psx_get_cycle_count) and counts.
```
t2probe.py fpcap  <port> native.json  4096 <flo> <fhi>   # native run
t2probe.py fpcap  <port> interp.json  4096 <flo> <fhi>   # PSX_OVERLAY_NATIVE_OFF=1 run
t2probe.py fpdiff native.json interp.json                # first divergent frame per column
```
`wr` differs ⇒ state fork. `pc` only ⇒ same writes, different path. `mmio`/`sp`
⇒ device/scratchpad fork. `cyc` ⇒ timing.

### Layer 2 — which ACCESS forks (frame-gated unified recorder)
Arm the recorder for the divergent frame N *before the run reaches it* — seed
`PSX_RECORD_FRAME=N` at boot (race-free; do NOT connect-and-arm, you'll lose the
race). It records every main-RAM/scratchpad/MMIO write **and** MMIO read for that
one frame, in true execution order (array index = order), each with `cyc`.
```
# launch with PSX_RECORD_FRAME=<N> (and PSX_OVERLAY_NATIVE_OFF=1 for the interp run)
t2probe.py recdump <port> native_rec.json
t2probe.py recdump <port> interp_rec.json
t2probe.py recdiff_state native_rec.json interp_rec.json  # first divergent RAM WRITE
```
Use **`recdiff_state`** (addr,val only) for the genuine state fork. Plain
`recdiff` includes `pc` and will flag benign store-PC attribution differences
(e.g. a RAM routine executed as a byte-identical BIOS alias) before the real
fork. MMIO read counts also differ benignly once the backends diverge, so don't
align reads by index.

### Layer 3 — value vs pointer vs timing
- **Read-watch**: `PSX_READ_WATCH="0xLO,0xHI"` at boot records main-RAM *reads*
  in `[LO,HI)` (kind `ramr`) interleaved in the recorder. Proves what value each
  backend loads from a suspect address, and whether it even reads it (pointer
  equality). Hot-path cost is one `int` flag check; off by default.
- **Per-entry `cyc`**: every recorder entry carries the cycle count, so you can
  see the exact cycle position at a divergent MMIO/timer read — distinguishing a
  timing/timer fork from a data fork.

Always confirm the end state **visually** (`shot.py`), not by a frame counter.

## Files
- `t2probe.py` — the probe (fpcap/fpdiff/recarm/recdump/recdiff/recdiff_state).
- `waitf.py` — retry-connect + poll until a target frame.
- `shot.py` — screenshot to PNG for visual verification.
- (`debug_client.py` lives one dir up in `tools/`.)

## Worked example — Tomba 2 logo→FMV stall (2026-06-24)
Frames 1..1822 byte-identical incl. scratchpad and cycle count. First fork at a
Timer1 (`0x1F801110`) debounce loop (game pc `0x8008592C`): native read 1, interp
read 2 → logo never advances to the intro FMV. Root cause was a guest-cycle
divergence: compiled-overlay code was built **without** `PSX_ENABLE_BLOCK_CYCLES`
so it charged ~0 cycles while the dirty-interp charged per-instruction. The
read-watch proved the jalr target was identical in both backends (`[a0]=0x800896E0`),
killing the "jalr divergence" theory; `recdiff_state` + per-entry `cyc` pinned the
Timer1 value fork; the `sp` column ruled out a scratchpad blind spot.

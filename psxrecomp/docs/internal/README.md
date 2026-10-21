# Internal dev-logs & design notes

These are the working design documents and burn-down logs the project was built
from. They are **historical/working notes**, not contributor onboarding docs —
they capture decisions, phased plans, and deep subsystem investigations in the
order they happened, and some sections are superseded by later ones.

If you're new here, start with the top-level [`README.md`](../../README.md),
then [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md),
[`docs/EXECUTION_MODEL.md`](../EXECUTION_MODEL.md),
[`docs/BUILDING.md`](../BUILDING.md), and
[`CONTRIBUTING.md`](../../CONTRIBUTING.md). Come here when you need the *why*
behind a specific subsystem.

## Plans & roadmap
- [`PLAN.md`](PLAN.md) — the original phased build plan (P1–P6).
- [`FAITHFUL_TIMING_PLAN.md`](FAITHFUL_TIMING_PLAN.md) — the authoritative
  cycle-accuracy north-star plan and status log.
- [`FIRST_MILESTONE.md`](FIRST_MILESTONE.md) — the first-boot milestone gate.
- [`STUBS_TO_FIX.md`](STUBS_TO_FIX.md) — hardware-stub burn-down (pre-game gate).

## Cycle accuracy & timing
- [`PRECISE_IRQ_SLICE.md`](PRECISE_IRQ_SLICE.md) — exact-instruction IRQ delivery.
- [`CYCLE_MODEL_BEETLE.md`](CYCLE_MODEL_BEETLE.md) — the Beetle-derived cycle model.
- [`ACCURACY_BURNDOWN.md`](ACCURACY_BURNDOWN.md) — full accuracy burn-down across
  all axes (semantics, cycle, IRQ, MMIO, peripherals, determinism).
- [`COSIM_ORACLE.md`](COSIM_ORACLE.md) — the first-divergence co-sim oracle.

## BIOS / scheduler
- [`HLE_SCHEDULER_CARVEOUT_PLAN.md`](HLE_SCHEDULER_CARVEOUT_PLAN.md) — the
  cooperative-thread scheduler HLE carve-out.
- [`WEDGE_load4_shell_rootcause.md`](WEDGE_load4_shell_rootcause.md) — a specific
  boot-shell wedge root-cause writeup.

## Renderer / widescreen
- [`GL_RENDERER_HANDOFF.md`](GL_RENDERER_HANDOFF.md) — OpenGL renderer design.
- [`NATIVE_WIDE_PLAN.md`](NATIVE_WIDE_PLAN.md) — native-wide 16:9 (GTE FOV) plan.
- [`BACKDROP_PRELOAD.md`](BACKDROP_PRELOAD.md) — widescreen backdrop preload.

## Overlay cache internals
- [`SLJIT_PERSIST_CACHE.md`](SLJIT_PERSIST_CACHE.md) — persisted overlay-shard
  cache design.

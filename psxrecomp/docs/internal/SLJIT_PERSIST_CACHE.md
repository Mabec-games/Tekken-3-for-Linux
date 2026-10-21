# Persisted sljit shard cache — design + work to be done

> **STATUS (implemented):** Stage 1 (position-independent shards via the
> cpu-relative `CPUState.sljit_helpers` table) and Stage 2 (serialize on JIT →
> `<cache>/<game>/sljit/<arch-abi>/cg<N>/<entry8>_<crc8>.sljit`, reload + regenerate
> at init, re-validate through the existing dispatch crc + diff gate) are both
> done and validated: a clean two-launch test reloaded 12 shards from disk and ran
> them at a fresh ASLR base with no stale-pointer crash, gameplay rendering
> correctly. KEY GOTCHA found in testing: `sljit_serialize_compiler` must run
> BEFORE `sljit_generate_code` (generate finalizes the compiler → `compiler->error
> = SLJIT_ERR_COMPILED` → serialize then returns NULL), and serialize with
> `options = 0` (NOT `IGNORE_DEBUG`) so an argument-checks build can deserialize.
> Persist timing is write-on-generate (negligible cost, crash-safe). The notes
> below are the original design.

Branch: `feat/sljit-persist-cache` (off `master` @ 0c1f005). Deferred from the
2026-06-15 sljit-default-on session because it has an **ASLR prerequisite** that
makes it a focused feature, not a quick add. In-session sljit re-JIT already
works (sljit is default-on, validated, gcc > sljit > interp); this feature only
adds **cross-session persistence** so subsequent launches reuse shards instead of
re-JITing the tail.

## Goal

> "sljit is supposed to have its own cache too — separate from gcc, lower
> priority. Load into memory in subsequent sessions any sljit shard that doesn't
> have a higher-priority gcc DLL." — user, 2026-06-15

Persist validated sljit shards to disk; reload them at startup; use a reloaded
shard only where no higher-priority gcc DLL covers the same function. Priority
stays **gcc > sljit > interp**.

## The blocker (why v1 punted, why Stage 1 exists)

`sljit_serialize_compiler()` serializes the LIR **verbatim, including immediate
operands**. Per sljitLir.h it restores jump *targets*, but NOT arbitrary
`MOV reg, IMM` operands. Our shards bake **absolute host function pointers** as
immediates, so a shard serialized in one process and reloaded in another calls
**stale addresses** (the runtime loads at a different base each launch — ASLR)
→ crash. So persistence is impossible until shards are position-independent
w.r.t. host pointers.

### The exact hazard sites (runtime/src/overlay_sljit.c, as of 0c1f005)

Three sites bake **four** distinct helper pointers via `SLJIT_IMM (uintptr_t)fn`:

| Site (fn) | line | helper(s) baked |
|---|---|---|
| `emit_helper2` | ~349 | `psx_sljit_memx`, `psx_sljit_cop2` (LWL/LWR/SWL/SWR, COP2/GTE, LWC2/SWC2) |
| `emit_ws_cull` | ~365 | `psx_ws_cull_sltiu` (widescreen render-funnel cull widen) |
| `PEND_CALL`    | ~921 | `psx_sljit_call` (jal/jalr call contract) |

The load/store icalls (~320/337) are **already reload-safe** — they load the fn
from `SLJIT_MEM1(R_CPU), offsetof(CPUState, read_word/write_word/...)`, i.e.
cpu-relative. That is the exact pattern Stage 1 copies for the helpers.

## Stage 1 — position-independent shards (PREREQUISITE, correctness-critical)

Route every host-helper call through a **cpu-relative helper-pointer table**
instead of a baked immediate, so the serialized LIR contains zero absolute host
addresses.

1. Add a fixed-order helper table reachable from `CPUState` (runtime/include/
   cpu_state.h). Either a `const void *const *sljit_helpers;` pointer field
   (append at END so existing gcc-DLL field offsets are unchanged — gcc codegen
   is unaffected; gcc DLLs resolve `psx_ws_cull_sltiu` via the loader's import
   fixups, not baked pointers, so ONLY sljit needs this) or an inline array.
2. Define a stable enum order, e.g.
   `enum { SLJIT_HLP_MEMX, SLJIT_HLP_COP2, SLJIT_HLP_WS_CULL, SLJIT_HLP_CALL, SLJIT_HLP_COUNT };`
   The order is part of the on-disk format — never reorder; only append. Fold
   the order/contents into a serialization version (see Stage 2 / cg<N>).
3. Populate the table once at startup (where CPUState is initialized) with the
   real addresses.
4. Change the 3 emit sites: instead of `MOV R2, IMM (uintptr_t)fn`, emit
   `MOV Rtab, MEM1(R_CPU)[offsetof(CPUState, sljit_helpers)]` then
   `MOV Rfn, MEM1(Rtab)[k*sizeof(void*)]` then icall `Rfn`. (`emit_helper2`
   takes a helper-enum index instead of a raw `fn`.) Mind scratch-register
   usage — the table load needs a scratch that doesn't clobber the call args
   (R0..R3 are args; use R4/a free scratch for the table+fn, as PEND_CALL
   already uses R4 for the fn ptr).
5. **This is a strict win on its own** and is independently testable: with
   Stage 1 alone (no disk cache yet), in-session JIT must still pass the existing
   live playtest (no regression: same shard behaviour, just one extra indirection
   per helper call). Verify before building Stage 2.

Risk: a missed/mis-ordered helper pointer = every shard that uses it crashes.
Test by exercising each helper class (a GTE-heavy scene for COP2, an unaligned
load for memx, a jal-heavy overlay for call, a 16:9 overlay-funnel scene for
ws_cull).

## Stage 2 — the disk cache (serialize / reload / re-validate)

Mirror the gcc cache layout + versioning exactly.

**Path:** `<cache_dir>/<game_id>/sljit/<arch-abi>/cg<N>/<phys8>_<crc8>.sljit`
(the `sljit/<arch-abi>/` namespace is already RESERVED in overlay_loader.c's
scan; `cg<N>` = `PSX_OVERLAY_CODEGEN_VER` from overlay_api.h, same as gcc — so a
codegen/emitter change auto-invalidates stale sljit blobs too. Also bump a
dedicated serialization tag if the helper-table order changes.)

**Serialize on compile** (overlay_sljit.c, after `sljit_generate_code` succeeds):
- `buf = sljit_serialize_compiler(C, SLJIT_SERIALIZE_IGNORE_DEBUG, &sz)` BEFORE
  `sljit_free_compiler(C)` (serialize doesn't modify the compiler, so order vs
  generate_code is flexible; keep both before free).
- Compute `crc_code` over live RAM `[entry_phys, entry_phys+frag_words*4)` with
  the same `crc32_compute` the loader uses (so the filename CRC matches what
  dispatch re-hashes).
- Write a small header + the serialized buffer:
  `{ magic, format_ver, helper_order_ver, entry_phys, code_lo, code_len,
     insns, crc_code, blob_size }` then the `sljit_uw` blob.
- Gate writing on a config/env (don't write during shadow/diff runs; only persist
  shards that have been VALIDATED — or persist eagerly and rely on reload-time
  re-validation, see below. Eager is simpler and safe given re-validation.).

**Reload at init** (overlay_loader.c, extend `scan_cache_dir`):
- Scan `sljit/<arch-abi>/cg<N>/*.sljit`. For each: read header, check
  magic/format/helper_order, `C = sljit_deserialize_compiler(blob, sz, 0, NULL)`,
  `code = sljit_generate_code(C, 0, NULL)`, `sljit_free_compiler(C)`.
- Register as a sljit candidate (`dll = -1`) over `[code_lo, code_len)` with
  `crc_code` — exactly like `register_sljit_candidate`, just sourced from disk.

**Re-validation (the safety model — no new trust surface):** a reloaded shard
is NOT trusted blindly. The existing dispatch path already (a) re-hashes live RAM
vs `crc_code` every dispatch (a shard for a different scene/variant simply never
matches → never runs), and (b) routes `dll<0` shards through the same-state diff
gate (`want_diff = s_sljit_live && c->dll < 0`) until the verify budget, with
device-touch/diverging shards pinned to interp. So a persisted shard re-earns
trust each session exactly like a fresh JIT. This is what makes Stage 2 safe.

**Priority gcc > sljit > interp:** unchanged — gcc DLLs register as `dll>=0` and
the existing obsolete logic (`sljit shard obsoleted by gcc DLL`) retires a sljit
shard when a gcc DLL covers the same live function. Ensure load order or the
dispatch chain keeps gcc ahead (gcc DLLs loaded lazily on dispatch miss via
`try_load_region`; persisted sljit shards loaded at init — confirm a gcc DLL that
arrives later still supersedes the pre-registered sljit shard).

## Verification plan

- Stage 1: in-session playtest unchanged (no crash, same diff stats) — gates
  Stage 2.
- Stage 2: launch once (populate the sljit cache), relaunch, confirm shards load
  from disk (`sljit_status` shows reloaded count), the game runs (no stale-pointer
  crash — proves Stage 1), gcc-covered functions still use gcc, and the
  native:interp ratio matches the in-session-JIT baseline. Force a helper-class
  per shard (GTE/memx/call/ws_cull) on reload to prove the indirection.
- 4:3 / widescreen-off unaffected throughout.

## Files

- `runtime/include/cpu_state.h` — helper table field (Stage 1).
- `runtime/src/overlay_sljit.c` — helper-table emit (Stage 1) + serialize (Stage 2).
- `runtime/src/overlay_loader.c` — reload + register at init (Stage 2); the
  `sljit/<arch-abi>/` scan is already reserved here.
- `runtime/include/overlay_api.h` — `PSX_OVERLAY_CODEGEN_VER` (+ a helper-order
  tag) gates the sljit blob namespace.
- startup (CPUState init site) — populate the helper table (Stage 1).

## Context (what already shipped on master, 0c1f005)

sljit is merged + default-on + validated; one shared `psx_ws_cull_sltiu` helper
is routed by gcc/sljit/interp (overlay 3D widens in 16:9 on every path); the gcc
cache is versioned `gcc/<arch-abi>/cg<N>/`. See `SLJIT.md`, `WIDESCREEN.md`, and
memory `sljit_backend_state` / `native_wide_fov_autocull`.

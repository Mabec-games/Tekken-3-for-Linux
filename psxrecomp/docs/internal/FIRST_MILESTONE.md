This is NOT "start the runtime".

This is a **controlled proof of correctness**.

---

## Scope

### Input
- bios/SCPH1001.BIN (524288 bytes)
- Loaded at virtual address: 0xBFC00000

### Target region (STRICT)
Only recompile:

- Reset vector entry: 0xBFC00000
- Linear control flow until:
  - First indirect jump (JR / JALR)
  - OR first exception return (ERET)
  - OR 4 KB of code max

WHICHEVER COMES FIRST.

---

## Required Outputs

### 1. Generated C file
- File: `generated/boot_slice.c`
- Must compile cleanly
- Must not be hand-edited

---

### 2. Function manifest (MANDATORY)

File: `generated/boot_slice_manifest.json`

Each entry MUST include:

```json
{
  "address": "0xBFC00000",
  "type": "function_entry",
  "discovered_by": "reset_vector",
  "instructions": 37,
  "ends_at": "0xBFC00094",
  "termination_reason": "jalr"
}
3. Unsupported instruction report

File: generated/unsupported_ops.json

If ANY instruction is not handled:

BUILD MUST FAIL
Entry must include:
{
  "address": "0xBFC0002C",
  "opcode": "COP0_MTC0",
  "reason": "not implemented"
}

NO SILENT FALLBACKS.

Rules
NO interpreter
NO HLE
NO stubs
NO skipping instructions
NO "approximation"
NO partial instruction support

If something is unknown → FAIL LOUDLY

Acceptance Criteria

ALL must be true:

boot_slice.c compiles
manifest exists and is complete
unsupported_ops.json is EMPTY
Every instruction in the slice is accounted for
No TODO / FIXME in generated code
Explicit Non-Goals
No runtime
No MMIO
No GPU
No interrupts
No full BIOS walk
Failure Conditions

Immediate failure if:

Any instruction is skipped
Any fallback logic is introduced
Any "temporary" behavior appears
Manifest is incomplete or missing
Why This Exists

v3 failed because it jumped straight to "running things"
without proving the recompiler was correct.

This milestone ensures:

→ decoding is correct
→ control flow is correct
→ codegen is correct

before ANY runtime exists.


---

# 🧠 2. BOOT_RELOCATION_PLAN.md (THIS PREVENTS FUTURE FAILURE)

```md
# BOOT_RELOCATION_PLAN.md — BIOS ROM → RAM Strategy

## Problem

The PS1 BIOS copies code from ROM (0xBFCxxxxx)
into RAM (0x800xxxxx) and executes it.

Naive recompilation causes:
- duplicate functions
- broken dispatch tables
- incorrect control flow

---

## Goal

Represent ROM and RAM code as **the same logical function**
with multiple address aliases.

---

## Rules

### 1. No duplicate code generation

If ROM code at:
0xBFC01234

is copied to:
0x8001234

Then BOTH must map to:

```c
void func_001234(...)

NOT:

func_BFC01234()
func_8001234()
2. Address normalization

All functions must be identified by:

normalized_address = address & 0x1FFFFFFF
3. Manifest requirement

File: generated/address_aliases.json

{
  "0xBFC01234": "0x80001234",
  "0xBFC05678": "0x80005678"
}

Must be generated ONLY when proven.

4. Proof requirement

An alias may ONLY be created if:

A memcpy/move loop is identified in Ghidra
Source + destination ranges match
Verified in DuckStation memory trace

NO GUESSING.

5. Dispatch tables

When BIOS builds tables:

Entries must point to normalized functions
Not raw ROM or RAM addresses
Failure Modes (DO NOT ALLOW)
Duplicate function bodies
Diverging ROM vs RAM behavior
Table entries pointing to different implementations
"Seems equivalent" logic
Enforcement

If a function is emitted twice:

→ BUILD FAILS

Why This Matters

This is the core reason PSX recompilation fails.

If this is wrong:

→ EVERYTHING breaks later
→ bugs become untraceable
→ project becomes v3 again


---

# 🧾 3. PROOF_REQUIREMENTS.md (THIS FIXES CLAUDE'S BS)

```md
# PROOF_REQUIREMENTS.md — No More Guessing

## Rule

Any claim must produce a machine-verifiable artifact.

---

## Required Proof Types

### Function Discovery

Must output:

- address
- how discovered (linear / table / jump target)
- termination reason

---

### Indirect Calls

Must output:

- source instruction
- resolved target
- how resolved

---

### Table Builds

Must output:

- table location
- source data
- final entries

---

### Relocation

Must output:

- source ROM range
- destination RAM range
- proof (Ghidra + runtime)

---

## Forbidden

- "probably"
- "looks correct"
- "should work"
- "seems like"
- "matches expectation"

---

## Required Language

Every statement must be:

- proven
- or explicitly unknown

---

## Failure Condition

If ANY conclusion lacks proof artifact:

→ INVALID WORK
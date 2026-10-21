# POSIX overlay discovery provenance

This change ports one focused capability from Douglas Vanderveer's PSXRecomp
work: Linux/macOS discovery of cached overlay libraries and manifest-driven
resolution of their `func_XXXXXXXX` exports.

The original implementation was developed while validating the
[R4 recompilation](https://github.com/douglasjv/r4) and appeared in Douglas's
framework commits
[`df7d1faa5f27be0ba357463a763c77efc43e1f91`](https://github.com/douglasjv/psxrecomp-tweaks/commit/df7d1faa5f27be0ba357463a763c77efc43e1f91)
and
[`7abbfdf38b488d3764b96c155549bc930e0521b6`](https://github.com/douglasjv/psxrecomp-tweaks/commit/7abbfdf38b488d3764b96c155549bc930e0521b6).
It is rebuilt here against the newer cache index, ABI tag, codegen namespace,
lazy manifest index, exact native dispatch, and rescan behavior on current
master. The earlier upstream context is
[mstan/psxrecomp PR #15](https://github.com/mstan/psxrecomp/pull/15).

Included scope:

- strict `<addr8>_<crc8>.dll` validation for both cache-key fields;
- POSIX directory enumeration with GCC-before-TCC deduplication;
- POSIX codegen-tag mismatch diagnostics and ABI preflight cleanup;
- manifest-authoritative `dlsym` registration, with failed/empty libraries
  closed and successful libraries retained while their function pointers live;
- additive, idempotent rescan behavior inherited from the current loader.

Explicitly excluded are frame splitting, SPU changes, forced-interpreter pages,
macOS GL context changes, CPU-copied overlay fallback, game configuration,
R4 addresses or timing policy, and all other R4-specific work.

The focused Linux test builds a real shared-library fixture, exercises strict
name parsing and directory filtering, detects a sibling codegen tag, resolves a
manifest-style `func_80012345` symbol, and verifies close/reopen behavior:

```sh
bash runtime/tests/run_overlay_posix_test.sh
```

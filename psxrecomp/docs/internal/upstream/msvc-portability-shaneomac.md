# MSVC portability from Shaneomac PR #16

## Source and credit

- Source PR: [mstan/psxrecomp#16](https://github.com/mstan/psxrecomp/pull/16)
- Source commit: [`df4cc5c70ab1e5d0fd2a8f817dd346905d4d0eeb`](https://github.com/mstan/psxrecomp/commit/df4cc5c70ab1e5d0fd2a8f817dd346905d4d0eeb)
- Author preserved by cherry-pick: Martin Penkava
  `<mpenkava1337@gmail.com>`.
- The source commit's Claude Fable 5 co-author trailer is also preserved.

## Adapted scope

The source commit was applied as a focused portability change:

- MSVC bit-scan intrinsics replace unavailable GCC/Clang builtins;
- generated CPS startup markers use an MSVC `.CRT$XCU` initializer and retain
  the constructor path for GCC/Clang; and
- runtime globals defined by C translation units receive explicit C linkage in
  the C++ entry point.

`recompiler/tests/test_msvc_cps_codegen.py` generates a minimal game dispatch
and checks that both compiler startup paths are emitted.

## Validation in this branch

- Visual Studio 2022/MSVC 19.41 built `psxrecomp-game`, `psxrecomp-bios`, and
  `l2_structural_test`; the structural suite passed 44/44.
- The MSVC-built game recompiler passed
  `test_msvc_cps_codegen.py` on generated output.
- A freshly generated BIOS runtime compiled all 63 C/C++ object steps under
  MSVC, including the new intrinsic and C-linkage paths. The final BIOS-only
  link remains blocked by the baseline's unrelated missing
  `psx_game_address_in_text` and `psx_game_text_native_ok` definitions. No
  change for that pre-existing game-symbol contract is included here.

## Explicitly excluded

No other PR #16 material was imported. In particular, this branch excludes the
SmackDown-specific batch files, dynamic-code discovery fallback, SPU changes,
primitive rejection, Vulkan diagnostics/optimization, and CRT shaders. Those
items require independent review and provenance records.

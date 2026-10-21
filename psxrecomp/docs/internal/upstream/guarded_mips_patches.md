# Guarded MIPS patch upstream provenance

This focused implementation was rebuilt for current `mstan/psxrecomp` from
Douglas's declarative-patch work in
[`mstan/psxrecomp` PR #15](https://github.com/mstan/psxrecomp/pull/15), exact
source commit
[`19001c0a383edde439988b93eb2385e2d789d350`](https://github.com/douglasjv/psxrecomp-tweaks/commit/19001c0a383edde439988b93eb2385e2d789d350).
The implementation keeps the original design: game-owned instruction data,
an exact opcode guard, replacement before ordinary MIPS-to-C translation, and
guarded overlay variants. This rebuild applies replacements before discovery
and control-flow analysis as well, so patched branches cannot leave the
generated graph based on stale bytes.

The upstreaming scope intentionally includes only:

- the typed `[[recompiler.patch]]` schema and loader;
- physical-alias-aware uniqueness and lookup;
- main-EXE failure on an opcode mismatch;
- overlay nonmatch pass-through;
- focused parser/code-generation tests and schema documentation.

It intentionally excludes all other work from PR #15 and subsequent Douglas
branches: signed widescreen bounds, textured-edge expansion, full-mirror
rendering, OpenGL context changes, CPU-copied-overlay fallback, debug/input
controls, and every game repository or title-specific address. Those concerns
require independent review and validation before any separate upstreaming.

Authorship from the source implementation is retained in the integrating
commit with:

```text
Co-authored-by: douglasjv <vanderveerdouglas@gmail.com>
```

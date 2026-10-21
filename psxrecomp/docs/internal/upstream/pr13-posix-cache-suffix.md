# PR #13 POSIX cache-suffix provenance

Parked from NyperYuhgard's PSXrecomp PR #13, commit
[`a39ab37dbc32f4889bf80331208b7510f497fc4f`](https://github.com/mstan/psxrecomp/commit/a39ab37dbc32f4889bf80331208b7510f497fc4f).

Native overlay artifacts use `.dll` on Windows and `.so` on POSIX hosts. The
compiler, cache parser, manifest lookup, ABI cleanup, and cached-CRC lookup share
that convention. POSIX loading/scanning itself is excluded because current master
already has the newer implementation merged through PR #18.

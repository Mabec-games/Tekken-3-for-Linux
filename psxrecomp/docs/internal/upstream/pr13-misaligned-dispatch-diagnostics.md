# PR #13 misaligned-dispatch diagnostics provenance

Parked from NyperYuhgard's PSXrecomp PR #13, commit
[`b07cb79251ecdca85aca94ba5dbfd731b67e10a7`](https://github.com/mstan/psxrecomp/commit/b07cb79251ecdca85aca94ba5dbfd731b67e10a7).

The fatal report now includes the recent dispatch tail and searches guest RAM for
the corrupt pointer and its aligned form. The hard-coded Crash Bash write-watch
range from the same upstream commit is deliberately excluded.

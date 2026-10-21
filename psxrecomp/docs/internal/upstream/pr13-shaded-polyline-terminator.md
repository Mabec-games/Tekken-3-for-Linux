# PR #13 shaded-polyline terminator provenance

Parked from NyperYuhgard's PSXrecomp PR #13, commit
[`2ba52e9754d672fb5efdb6f8cba49c82f27a8734`](https://github.com/mstan/psxrecomp/commit/2ba52e9754d672fb5efdb6f8cba49c82f27a8734).

The GP0 shaded-polyline terminator is checked before alternating color/vertex
decoding, so the hardware terminator is accepted in either stream position. All
other GPU, DMA, CD-ROM, MDEC, and SPU changes from the mixed upstream commit are
intentionally excluded from this focused branch.

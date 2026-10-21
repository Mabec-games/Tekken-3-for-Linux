# PR 14 software-raster triangle coverage

Evaluated and adapted on 2026-07-14 from Kareem Olim's
[PR #14](https://github.com/mstan/psxrecomp/pull/14), exact commit
[`91a654f61dff18806f3eea43f72a30cb34430695`](https://github.com/mstan/psxrecomp/commit/91a654f61dff18806f3eea43f72a30cb34430695).

Adapted scope: the software rasterizer's biased 32.32 edge DDA and half-open
bottom/right triangle coverage for flat, Gouraud, textured, and shaded-textured
triangles. The reusable edge math was moved to a small tested internal header.

Excluded: all title references, WebAssembly work, CD/SPU changes, GTE subpixel
and perspective experiments, presentation blending, and every other PR #14
change. This branch changes only software triangle coverage.

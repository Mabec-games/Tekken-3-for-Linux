# PR #14 duplicate-frame presentation smoothing

Source: [kem0x PR #14](https://github.com/mstan/psxrecomp/pull/14), commit
[`ec889d6e5956fc4f34acfee41d87f30b24123b7f`](https://github.com/mstan/psxrecomp/commit/ec889d6e5956fc4f34acfee41d87f30b24123b7f).

This branch generalizes the source's presentation-only 30-to-60 Hz experiment:
when software output repeats an exact guest image for two vblanks, the next
distinct image is presented first as a temporal midpoint. A scene-cut heuristic
avoids blending unrelated images. Guest execution, SPU timing, and GPU-direct or
FMV paths remain untouched. It is off by default, exposed through a generic C
setter, a Web export, and `PSX_SMOOTH_60FPS`.

The smoother is mutually exclusive with the existing software frame-blend
masker. It is distinct from master's GL high-refresh interpolation path.

Excluded: every title name, address, state hook, and scripted action from the
source commit. Authorship is retained in the commit trailer.

# Tekken 3 native PC port

This directory is the clean-room, host-native port. It is deliberately a
different executable from `psx-runtime`:

- no translated MIPS functions or guest RAM;
- no PlayStation BIOS, scheduler, GTE, GPU command processor, or interpreter;
- native fixed-step match simulation and hit detection;
- native OpenGL scene renderer with aspect-correct perspective;
- read-only access to a legally owned disc through the neutral CUE/ISO layer.

The first vertical slice is intentionally procedural while the original model
formats are mapped. It proves the executable, simulation/render boundary,
independent disc verification, input, resize/fullscreen handling, and true
16:9 camera contract. It is not yet a content-complete port.

Build and test from the repository root:

```powershell
.\scripts\dev.ps1 native-build
.\scripts\dev.ps1 native-test
.\scripts\dev.ps1 native-capture
.\scripts\dev.ps1 native-run
```

Controls are A/D to move, W or Space to jump, J/K to attack, R to reset the
round, F11 for fullscreen, and Escape to quit.

The next content milestone is one trace-validated stage importer. Geometry,
UVs, texture page/CLUT state, draw order, collision and background layers must
be decoded into a lossless native scene representation before the procedural
stage is replaced. Fighter skeletons and animations follow that stage proof.

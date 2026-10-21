# PR #13 FPS telemetry provenance

Parked from NyperYuhgard's PSXrecomp PR #13, commit
[`b49548e7b8f494c9584eb09039a8c325d7375b46`](https://github.com/mstan/psxrecomp/commit/b49548e7b8f494c9584eb09039a8c325d7375b46).

This branch retains only the simulated-vblank FPS and realtime-speed telemetry.
It was adapted to current master, guards window-title access in
headless/windowless operation, and is disabled by default. Set
`PSX_FPS_TELEMETRY=1` before launch to opt in to the title-bar counter and
matching stderr line. The overlay-cache inventory from the same upstream commit
is parked separately.

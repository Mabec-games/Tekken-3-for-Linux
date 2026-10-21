# PR #13 overlay-cache inventory provenance

Parked from NyperYuhgard's PSXrecomp PR #13, commit
[`b49548e7b8f494c9584eb09039a8c325d7375b46`](https://github.com/mstan/psxrecomp/commit/b49548e7b8f494c9584eb09039a8c325d7375b46).

Set `PSX_OVERLAY_CACHE_INVENTORY=1` to print every indexed native overlay shard
after a cache scan. The upstream change printed unconditionally; this adaptation
keeps current master's no-routine-stderr policy by making the diagnostic opt-in.
FPS telemetry from the same upstream commit is parked separately.

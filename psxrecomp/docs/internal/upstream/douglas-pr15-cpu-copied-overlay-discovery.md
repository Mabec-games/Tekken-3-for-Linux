# CPU-copied overlay discovery experiment

Source: [PSXRecomp PR #15](https://github.com/mstan/psxrecomp/pull/15),
commit [`df7d1faa5f27be0ba357463a763c77efc43e1f91`](https://github.com/douglasjv/psxrecomp-tweaks/commit/df7d1faa5f27be0ba357463a763c77efc43e1f91).

This branch isolates the broad dispatch fallback used for overlays copied by
guest CPU stores. It is experimental because any dispatch above the configured
overlay floor becomes interpreter-eligible; the macOS GL and debug-input parts
of the source commit are excluded.

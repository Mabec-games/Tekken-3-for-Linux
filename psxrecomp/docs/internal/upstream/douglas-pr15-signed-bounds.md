# Typed widescreen signed bounds

Source: [PSXRecomp PR #15](https://github.com/mstan/psxrecomp/pull/15),
commit [`f44f365eb91a30396f05f0f52529d4b01b026099`](https://github.com/douglasjv/psxrecomp-tweaks/commit/f44f365eb91a30396f05f0f52529d4b01b026099).

This branch isolates the opt-in guarded LUI transform across static generation,
captured overlays, SLJIT, and the dirty interpreter. The source behavior is
parked for testing with two known review questions: runtime registration clamps
at 64 sites and scaling currently includes the renderer cull margin. Textured
edges, debug tooling, and title-specific addresses are excluded.

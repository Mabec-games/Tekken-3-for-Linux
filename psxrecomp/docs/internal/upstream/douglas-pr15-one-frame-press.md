# One-frame debug input pulse

Source: [PSXRecomp PR #15](https://github.com/mstan/psxrecomp/pull/15),
commit [`f44f365eb91a30396f05f0f52529d4b01b026099`](https://github.com/douglasjv/psxrecomp-tweaks/commit/f44f365eb91a30396f05f0f52529d4b01b026099).

This branch isolates the fix that returns an armed input pulse before consuming
its final frame. Widescreen signed bounds and unrelated debug tooling from the
source commit are excluded.

# macOS OpenGL context setup

Source: [PSXRecomp PR #15](https://github.com/mstan/psxrecomp/pull/15),
commit [`df7d1faa5f27be0ba357463a763c77efc43e1f91`](https://github.com/douglasjv/psxrecomp-tweaks/commit/df7d1faa5f27be0ba357463a763c77efc43e1f91).

This branch isolates the reusable OpenGL 3.3 core-context setup and applies it
to both launcher and direct game windows. CPU-copied overlay discovery, debug
input additions, and title-specific material from the source commit are not
included.

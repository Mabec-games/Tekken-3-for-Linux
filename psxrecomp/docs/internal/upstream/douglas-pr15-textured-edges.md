# Typed native-wide textured edge expansion

Source: [PSXRecomp PR #15](https://github.com/mstan/psxrecomp/pull/15),
commit [`cab3946855e74918d3ce006062d3e1b843b155d6`](https://github.com/douglasjv/psxrecomp-tweaks/commit/cab3946855e74918d3ce006062d3e1b843b155d6).

This branch preserves the source feature for direct temperature testing. It is
opt-in. The known review question is software-renderer parity: the GL path
distinguishes outside-edge expansion from ordinary backdrop stretch, while the
software path currently consumes the gate as a boolean. Signed bounds and
title-specific configuration are excluded.

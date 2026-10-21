# Debug client command parity

Source: [PSXRecomp PR #15](https://github.com/mstan/psxrecomp/pull/15),
commit [`f44f365eb91a30396f05f0f52529d4b01b026099`](https://github.com/douglasjv/psxrecomp-tweaks/commit/f44f365eb91a30396f05f0f52529d4b01b026099).

This branch exposes existing runtime debug-server operations through the Python
client: frame RAM reads, turbo-load control, richer write-trace filters, and the
always-on trace ring. Analog input and widescreen behavior are excluded.

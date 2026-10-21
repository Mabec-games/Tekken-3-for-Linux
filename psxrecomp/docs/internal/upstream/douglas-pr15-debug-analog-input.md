# Analog debug input and observability

Source: [PSXRecomp PR #15](https://github.com/mstan/psxrecomp/pull/15),
commits [`df7d1faa`](https://github.com/douglasjv/psxrecomp-tweaks/commit/df7d1faa5f27be0ba357463a763c77efc43e1f91)
and [`31cdfb4f`](https://github.com/douglasjv/psxrecomp-tweaks/commit/31cdfb4f4dac305e98661dfdbf8e685533fd7ca4).

This branch lets a debug `press` carry analog axes and reports live and
overridden stick values through `pad_status`. Widescreen, overlay discovery,
and unrelated debug commands are excluded.

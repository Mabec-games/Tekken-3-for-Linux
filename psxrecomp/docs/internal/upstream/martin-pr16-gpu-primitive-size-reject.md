# PR #16 GPU primitive-size rejection provenance

This branch isolates Martin Penkava's hardware primitive-size rejection from
[`mstan/psxrecomp` PR #16](https://github.com/mstan/psxrecomp/pull/16), exact
source commit
[`cfc5d0eab94c7ddfd30ed23c4d3beecdc737c835`](https://github.com/mstan/psxrecomp/commit/cfc5d0eab94c7ddfd30ed23c4d3beecdc737c835).

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` |
| Pull request/source commit | `mstan/psxrecomp` PR #16, `cfc5d0eab94c7ddfd30ed23c4d3beecdc737c835` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `fix/pr16-gpu-primitive-size-reject-mpenkava` |

The 1023-pixel horizontal and 511-pixel vertical limits are PS1 hardware rules
documented by No$PSX and implemented by independent emulators including Beetle
and DuckStation. The framework checks parsed coordinates before widescreen and
draw-offset transforms. Every flat, shaded, textured, and shaded-textured
polygon path is covered; quads reject each rendered triangle independently.
Mono/shaded lines and both polyline continuations use the same limits. Textured
commands still latch their texture-page state before a size rejection.

The source commit's game name and observed scenes are validation evidence only;
no title identifier, address, or configuration is included here.

Source authorship is retained with:

```text
Co-authored-by: Martin Penkava <mpenkava1337@gmail.com>
Co-authored-by: Claude Fable 5 <noreply@anthropic.com>
```

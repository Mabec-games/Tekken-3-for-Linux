# Martin Penkava PR #16: launcher Vulkan option

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `d05d14bb11caafad2963abe824f249249a80cb11` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `feat/pr16-launcher-vulkan-option-mpenkava` |

## Included scope

Adds Vulkan to the launcher's renderer cycle and label. The runtime already recognizes renderer value `2` as Vulkan; this exposes that existing backend through the graphical launcher while keeping OpenGL-only controls gated to renderer value `1`.

## Deliberate exclusions

- Vulkan backend correctness/performance changes are isolated on their own branches.
- CRT presentation, diagnostics, and game-specific data are excluded.

The source commit has no secondary co-author trailer; only Martin Penkava is credited in the local commit trailer.

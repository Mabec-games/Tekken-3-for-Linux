# Martin Penkava PR #16: Vulkan command-buffer batching

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `d05d14bb11caafad2963abe824f249249a80cb11` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `perf/pr16-vulkan-command-buffer-batching-mpenkava` |

## Included scope

Records the backend's small logical work operations into one open Vulkan command buffer and submits that buffer at the existing GPU synchronization point. This removes hundreds of per-operation command-buffer submissions while retaining command recording order and existing image barriers.

## Deliberate exclusions

- Persistent staging allocation reuse and present-mode policy are isolated on separate branches.
- Present timing telemetry and the earlier `PSX_VK_*` WIP diagnostics are excluded.
- CRT shaders, CRT pipeline objects, screen-kind routing, and game-specific data are excluded.

The source commit has no secondary co-author trailer; only Martin Penkava is credited in the local commit trailer.

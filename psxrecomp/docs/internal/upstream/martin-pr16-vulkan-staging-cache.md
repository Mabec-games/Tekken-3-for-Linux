# Martin Penkava PR #16: Vulkan persistent staging cache

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `d05d14bb11caafad2963abe824f249249a80cb11` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `perf/pr16-vulkan-staging-cache-mpenkava` |

## Included scope

Reuses up to 16 best-fit, persistently mapped host-visible staging buffers after the existing queue-idle reclamation point. This avoids repeated Vulkan buffer allocation, memory allocation, mapping, unmapping, and destruction on CPU-heavy upload frames.

The local extraction also removes a shutdown double-free hazard in the submitted version: the long-lived CPU-present staging buffer is explicitly removed from the shared cache before the remaining cache entries are destroyed. Uncached overflow entries are explicitly unmapped before destruction.

## Deliberate exclusions

- Command-buffer batching and present-mode policy are isolated on separate branches.
- Present timing telemetry and the earlier `PSX_VK_*` WIP diagnostics are excluded.
- CRT shaders, CRT pipeline objects, and game-specific data are excluded.

The source commit has no secondary co-author trailer; only Martin Penkava is credited in the local commit trailer.

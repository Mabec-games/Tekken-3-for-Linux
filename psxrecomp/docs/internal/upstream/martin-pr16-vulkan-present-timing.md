# Martin Penkava PR #16: Vulkan present timing telemetry

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `d05d14bb11caafad2963abe824f249249a80cb11` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `feat/pr16-vulkan-present-timing-telemetry-mpenkava` |

## Included scope

Extends the existing `vk_perf` ring with a presentation timestamp and microsecond durations for queue-idle waits, swapchain acquisition, and queue presentation. The JSON debug-server response exposes all four fields for frame-pacing diagnosis.

## Deliberate exclusions

- Command-buffer batching, staging reuse, and present-mode policy are isolated on separate branches.
- The earlier environment-gated VRAM dump/verification diagnostics are excluded.
- CRT presentation and game-specific benchmark commentary are excluded.

The source commit has no secondary co-author trailer; only Martin Penkava is credited in the local commit trailer.

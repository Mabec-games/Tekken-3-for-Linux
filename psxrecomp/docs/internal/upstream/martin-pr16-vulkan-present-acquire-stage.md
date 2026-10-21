# Martin Penkava PR #16: Vulkan present acquire wait stage

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `4517bd5a3ed0901a2402ff7b93bebe3de2cf9afd` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Source co-author trailer | Claude Fable 5 `<noreply@anthropic.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `fix/pr16-vulkan-present-acquire-stage-mpenkava` |

## Included scope

The swapchain acquire semaphore is waited at the transfer stage as well as color-attachment output. The presentation command buffer performs transfer clears/blits, so those writes must be ordered after acquisition on strict drivers.

## Deliberate exclusions

- Packed upload alignment and render-pass color self-barriers are isolated on separate branches.
- All `PSX_VK_*` WIP diagnostics from the source commit are excluded.
- CRT shaders and the later presentation redesign are excluded.

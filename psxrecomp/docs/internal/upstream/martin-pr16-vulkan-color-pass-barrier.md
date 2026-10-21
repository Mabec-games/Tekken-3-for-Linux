# Martin Penkava PR #16: Vulkan color pass self-barrier

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `4517bd5a3ed0901a2402ff7b93bebe3de2cf9afd` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Source co-author trailer | Claude Fable 5 `<noreply@anthropic.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `fix/pr16-vulkan-color-pass-barrier-mpenkava` |

## Included scope

Adds an explicit color-attachment memory dependency between back-to-back geometry, wide-surface, and wide-clear render passes when the image remains in `COLOR_ATTACHMENT_OPTIMAL`. This mirrors the existing depth/stencil ordering and covers drivers that do not tolerate the missing external dependency.

## Deliberate exclusions

- Packed upload alignment and swapchain acquire synchronization are isolated on separate branches.
- All `PSX_VK_*` WIP diagnostics from the source commit are excluded.
- CRT shaders and the later presentation redesign are excluded.

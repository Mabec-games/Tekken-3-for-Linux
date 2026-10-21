# Martin Penkava PR #16: Vulkan packed-upload alignment

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `4517bd5a3ed0901a2402ff7b93bebe3de2cf9afd` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Source co-author trailer | Claude Fable 5 `<noreply@anthropic.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `fix/pr16-vulkan-upload-alignment-mpenkava` |

## Included scope

Packed CPU-to-GPU upload regions are padded to an even texel count so every R16 `VkBufferImageCopy.bufferOffset` remains four-byte aligned. The copied image extents are unchanged.

## Deliberate exclusions

- Vulkan render-pass and acquire-semaphore synchronization are isolated on separate branches.
- All `PSX_VK_*` WIP diagnostics from the source commit are excluded.
- CRT shaders, presentation redesign, game-specific data, and scripts are excluded.

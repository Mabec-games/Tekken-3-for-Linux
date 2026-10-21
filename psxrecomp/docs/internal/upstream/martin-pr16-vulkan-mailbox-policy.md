# Martin Penkava PR #16: Vulkan MAILBOX tear-free policy

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `d05d14bb11caafad2963abe824f249249a80cb11` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `perf/pr16-vulkan-mailbox-tear-free-mpenkava` |

## Included scope

The tear-free Vulkan policy prefers MAILBOX because PSXRecomp's frontend already paces frames. If MAILBOX is unavailable, Vulkan's required FIFO mode remains the fallback; the explicit tearing policy still requests IMMEDIATE.

## Deliberate exclusions

- Source-commit benchmark comments naming a particular game are omitted; the policy itself is title-independent.
- Command-buffer batching and staging reuse are isolated on separate branches.
- Timing diagnostics, CRT presentation, and game-specific data are excluded.

The source commit has no secondary co-author trailer; only Martin Penkava is credited in the local commit trailer.

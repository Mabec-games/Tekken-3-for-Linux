# PR #13 generic boot write-watch provenance

Extracted from NyperYuhgard's PSXrecomp PR #13, commit
[`b07cb79251ecdca85aca94ba5dbfd731b67e10a7`](https://github.com/mstan/psxrecomp/commit/b07cb79251ecdca85aca94ba5dbfd731b67e10a7).

The upstream change identified a suspicious Crash Bash write by adding an
environment-gated watcher for the hard-coded physical range
`0x000B3A80..0x000B3AFF`. This extraction preserves the useful behavior while
removing the title-specific address and stderr-only reporting:

- `PSX_WTRACE_BOOT` accepts one or more caller-selected half-open ranges.
- Ranges feed the existing boot-pinned write trace from instruction zero.
- Retained records include PC, return address, register context, frame, width,
  and DMA attribution and remain queryable later through the TCP debug server.

The companion misaligned-dispatch diagnostics from the same source commit were
previously extracted in PR #28.

## Reproduction note

A verified retail Greatest Hits Crash Bash build exercised with the generic
range did write the watched address, confirming that the address and mechanism
are plausible. In that build, however, the nonzero write at physical
`0x000B3AC4` was the MIPS instruction word `0x8C65B690`, written by guest PC
`0x80048FA8` at frame 395. It did not reproduce the originally reported
`0x6766BD35` pointer value. For that reason this extraction exposes the
diagnostic generically and does not encode the unconfirmed title-specific
interpretation.

# kem0x PR #14: SPU END-without-REPEAT behavior

Evaluated on 2026-07-13 against psxrecomp master `dde268dc0fb9daf8fe6529f4aebfe80995350334`.

## Source and credit

- Pull request: [mstan/psxrecomp#14](https://github.com/mstan/psxrecomp/pull/14)
- Evaluated commit: [`b2597df6d5905a0e183b5309a9b84720cd417e19`](https://github.com/mstan/psxrecomp/commit/b2597df6d5905a0e183b5309a9b84720cd417e19)
- Original author: Kareem Olim (`Kareem Olim <kareemolim@gmail.com>`)

The generic behavior identified in that commit is that an ADPCM block carrying
END without REPEAT must redirect decoding to the voice's repeat address, enter
Release, and immediately clear the envelope. This prevents a one-shot voice
from leaking or looping unrelated sample RAM after its terminator.

Current master already implements the same behavior independently in commit
`462e2bf5fdb4d46b935322bf7f782fd424aea584`. Therefore this branch does not
replace that runtime code. It adds a focused regression test that pins the
shared behavior: END-only becomes silent and inactive at the boundary, resumes
decoding at the repeat address, and emits one stop event; END+REPEAT remains
audible and active.

## Explicit exclusions

The following material from the source commit was reviewed and intentionally
not imported:

- `PEPSIMAN_SFX_RETRIGGER_GUARD` and its address-based burst/cooldown policy:
  game-specific compensation for Pepsiman timing, not generic SPU behavior.
- The `PSX_WEB` reduction of `SPU_EVENT_CAP`: WebAssembly memory sizing is
  unrelated to ADPCM END semantics and belongs in a separate change.
- `SpuVoice.start_addr`: introduced for the excluded retrigger policy and not
  needed for the generic END transition.
- All other PR #14 changes: CD-ROM interrupts, CD-DA, raster timing, build
  changes, and game-specific hooks require independent review and branches.

No Pepsiman compile-time hook or game-specific playback heuristic is present in
this branch.

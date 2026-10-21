# Martin Penkava PR #16: SPU Gaussian interpolation

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` (submitted as `mstan/psxrecomp` PR #16) |
| Source commit | `e069c8a531b14c2ec4566d6a3dd5b1816a5600e6` |
| Source author | Martin Penkava `<mpenkava1337@gmail.com>` |
| Source co-author trailer | Claude Fable 5 `<noreply@anthropic.com>` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `feat/pr16-spu-gaussian-interpolation-mpenkava` |

## Included scope

- The 512-entry PS1 SPU Gaussian coefficient table introduced by the source commit.
- Four-tap hardware Gaussian interpolation of decoded ADPCM voice samples.
- Preservation of the preceding ADPCM block's final three samples so interpolation remains continuous at block boundaries.
- A standalone regression test covering the boundary-history tap order and the equivalent in-block window.

## Deliberate exclusions

- The reverb engine and reverb register handling from the same source commit are isolated on a different branch.
- The source commit's high-quality shadow/reverb gating is not needed for the dry Gaussian path and is excluded.
- No game-specific addresses, generated code, configuration, or scripts are included.

## Provenance note

The source header identifies the coefficient values as the documented PS1 hardware table from No$PSX documentation and DuckStation's `core/spu.cpp`. The values are hardware data; this branch preserves Martin Penkava's implementation provenance and exact authorship trailers. No DuckStation implementation code was imported here.

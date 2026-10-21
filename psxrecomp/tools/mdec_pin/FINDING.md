# MDEC pin — finding + RESOLUTION (2026-06-27)

## The bug (FOUND + FIXED)
The faithful dequant/IDCT/YUV transcription was correct, but the **15bpp pack lost the
uint8 truncation** Beetle's `RGB_to_RGB555(uint8 r,g,b)` performs implicitly:

    int ru = r ^ 0x80;            // r = Mask9ClampS8 ∈ [-128,127], a SIGNED int
    ... rgb_to_555_chan(ru) ...   // (c+4)>>3 on a possibly-NEGATIVE int → garbage

For negative `r`, `r ^ 0x80` is a negative int (e.g. r=-1 → -129), and the old
`rgb_to_555_chan(int)` did `(c+4)>>3` on it without truncating to 0..255. Beetle passes
the value through `uint8` params, truncating first. Result on real FMV: B saturated to
31, R/G ~doubled → the rainbow fringing. The 24bpp path was unaffected (it already casts
to `uint8_t`). FIX: `rgb_to_555_chan(uint8_t c)` (caller's `int` truncates on the call),
matching Beetle. mdec.c:rgb_to_555_chan.

## Why both pins initially MISSED it (important)
`mdec_pin.c` and `mdec_e2e.c`'s reference both computed the 555 channel on the same
un-truncated `int` — i.e. the reference REPLICATED mdec.c's bug, so they agreed (0 diffs)
while BOTH diverged from real Beetle. A standalone pin whose oracle is your own
transcription cannot catch an error shared by both. The truth came from the
**real Beetle process**: a `vram_peek` added to beetle_debug_server.c, diffing our VRAM
vs Beetle's VRAM at the held FMV (the gold-standard oracle). That collapsed the channel
deltas from mean (dR 12, dG 16, dB 27) to (0.7, 0.9, 1.3) and removed the rainbow.

## Validation now
- `mdec_e2e.c` full-path pin (with the corrected uint8 oracle): byte-exact.
- Live VRAM vs real Beetle: rainbow gone, FMV renders natural colours; residual <1.3
  mean (sub-LSB / Beetle's upscaled-VRAM representation + free-running frame mismatch).
LESSON: validate against the REAL oracle process, not a self-transcribed reference.

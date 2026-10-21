# Strict local TIM PNG re-encoder

`tim_import.py` re-encodes pixels from an identical-dimension RGBA PNG into
one standalone standard PlayStation TIM. The original `.tim` is the layout
contract: the output retains its header, VRAM coordinates, section geometry,
indexed CLUT bytes and 24bpp row padding, and has exactly the same byte size.

This is deliberately a private, local staging tool. Its `.tim` output still
contains bytes copied from the original game and is therefore a derived
artifact, not an independently authored or automatically redistributable
file. A public mod can distribute an independently authored PNG plus the
settings/recipe and regenerate the staging TIM from each user's verified
original locally. Redistribute a rebuilt whole TIM only with rightsholder
permission or proof that every redistributed byte is independently authored.
An edited preview containing retail art is not automatically safe to publish.

## Command

Extract a standalone TIM and its first preview with `tim_tool.py`, edit a copy
of the PNG without changing its canvas, then run:

```powershell
python tools/tim_import.py `
  --original workspace/textures/tim_0000_off_00001F58.tim `
  --png workspace/authoring/texture.png `
  --output workspace/staging/texture.tim `
  --report workspace/staging/texture.json
```

Existing outputs are preserved. `--force` replaces the output and report but
can never overwrite either input. The original must contain exactly one TIM
with no prefix or trailing data. The output is another standalone TIM; this
tool does not reinsert it into an ARC/BNS record or build a release package.

The default policies are lossless with respect to the supported PS1 color
representations. Two explicit, deterministic RGB quantizers are available:

```powershell
# 4/8bpp: choose only from the unchanged existing palette.
python tools/tim_import.py ... --nearest-palette

# 16bpp: round each RGB8 channel to RGB555.
python tools/tim_import.py ... --quantize-16bpp
```

The flags are mode-specific and are rejected on unrelated TIM modes. There is
no palette replacement mode: indexed CLUT data is always byte-for-byte
preserved.

## Exact supported cases

| TIM mode | Default import | Explicit option | Preserved data |
|---|---|---|---|
| 4bpp indexed | Every RGBA pixel must exactly match the sole 16-color palette. | `--nearest-palette` selects the nearest RGB in the same alpha/STP class. | Header, one-palette CLUT, section geometry and packed layout. |
| 8bpp indexed | Every RGBA pixel must exactly match the sole 256-color palette. | `--nearest-palette` selects the nearest RGB in the same alpha/STP class. | Header, one-palette CLUT, section geometry and packed layout. |
| 16bpp direct | RGB channels must be exact round trips of 5-bit channels. | `--quantize-16bpp` rounds RGB8 channels deterministically to RGB555. | Header, image geometry and VRAM coordinates. |
| 24bpp direct | RGB8 values are written exactly; alpha must be 255. | None. | Header, image geometry, VRAM coordinates and each row's 0-2 padding bytes. |

Indexed TIMs with zero or multiple palettes are rejected. When an exact color
appears more than once, an unchanged pixel retains its original index;
otherwise the lowest matching index wins. Nearest-palette distance is squared
Euclidean RGB distance, with the lowest index as the tie-breaker. It never
crosses transparency/STP classes and never changes a CLUT word.

For 16bpp explicit quantization, each channel uses
`(channel * 31 + 127) // 255`. A pixel already matching its original decoded
RGBA retains the exact original word. This preserves byte identity for a
preview round trip, including otherwise equivalent representations.

## PNG and alpha contract

The PNG decoder intentionally accepts a narrow, reproducible subset:

- exact TIM width and height, positive dimensions, and a bounded decoded size;
- PNG color type 6, 8 bits per channel, non-interlaced RGBA;
- valid CRCs, one first-position IHDR, consecutive IDAT chunks and an exact
  IEND with no trailing bytes;
- standard row filters 0 through 4 and one complete zlib stream;
- no APNG chunks, no optional PLTE chunk, and no other unsupported critical
  chunks.

Ancillary metadata is ignored and no gamma/profile color conversion is
performed: the stored RGBA bytes are the input. Paletted, grayscale, RGB-only,
16-bit-channel and interlaced PNGs are rejected rather than converted.

The alpha values are an explicit representation of the TIM preview convention:

- `RGBA(0,0,0,0)` selects/encodes PS1 color word zero;
- alpha `128` selects an existing STP-set indexed color or sets STP in 16bpp;
- alpha `255` selects/encodes a non-STP color;
- every other alpha value is ambiguous and rejected.

Transparent pixels with hidden nonzero RGB are rejected. In 16bpp, opaque
black is also rejected because non-STP word zero is interpreted as transparent.
For indexed nearest mapping, the palette must already contain at least one
entry in the requested alpha class. STP's actual blend result remains dependent
on the game's draw mode; alpha 128 identifies the bit and does not simulate
hardware blending.

## Output and report guarantees

After encoding, the tool reparses the output and checks its exact size, flags,
dimensions and section descriptors against the original. The JSON report
records input/output SHA-256 values, dimensions, mode, policy, changed-pixel
count, preservation assertions, and
`artifact_status: private_local_derived_staging_artifact`.

The guarantee is structural, not behavioral: a size-valid texture can still
look wrong in game because of UVs, palettes, draw-mode state or surrounding
container semantics. Test local reconstructions against the original game.

## Private validation on the exact US disc

Read-only validation used the locally owned `SLUS-00402` executable with
SHA-256
`fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c`.
A strict scan of all 303 top-level BNS records found 8,098 single-palette 4bpp
TIMs, 457 single-palette 8bpp TIMs, one four-palette 4bpp TIM, and no strict
16bpp or 24bpp TIMs.

Three previews extracted from private record `073` were imported with the
default policy. Every output was exact-size and byte-for-byte identical:

| Record-relative offset | Mode and dimensions | Size | SHA-256 |
|---|---:|---:|---|
| `0x1F58` | 8bpp, 32x64 | 2,592 | `3039bab2cc0a8c0900c3aca218dc2ae493ec971daae700b3c331d4cfefc1f1c4` |
| `0x2978` | 4bpp, 32x64 | 1,088 | `311a73cadd1b485d65f54236e799c0b8f23c14f9930e2f297a7fdde19241b9` |
| `0x2DB8` | 4bpp, 32x40 | 704 | `d505cf6a7c0715f33606850a683e29a347be5ef40f18a8842eb2fd5361c9c2cf` |

The real four-palette 4bpp TIM in record `301` at record-relative offset
`0x266A4` was rejected with the expected “requires exactly one palette” error.
Because this disc scan exposed no strict direct-color samples, 16bpp and 24bpp
round trips are covered by deterministic synthetic fixtures, not claimed as
private retail validation. No disc or extracted retail payload is committed.

Run the tests with:

```powershell
python -m unittest tools.tests.test_tim_import -v
```

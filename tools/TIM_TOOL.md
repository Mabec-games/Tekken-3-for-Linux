# Local TIM texture scanner and preview exporter

`tim_tool.py` finds standard PlayStation TIM images embedded in a locally
extracted BNS record or any other binary file. It exports the exact `.tim`
bytes plus deterministic PNG previews using only the Python standard library.
It never modifies its input.

All extracted TIM and PNG files may depict copyrighted game art. Keep them in
the gitignored `workspace/` or `out/` directories and do not include them in a
source or runtime release.

## Inventory a BNS record

First use `bns_tool.py` to extract the top-level record locally. Then scan that
record without writing any image payloads:

```powershell
python tools/tim_tool.py inventory `
  --source workspace/bns/entries/073.arc `
  --json workspace/textures/073-inventory.json
```

Omit `--json` to write the inventory to standard output. An existing JSON file
is preserved unless `--force` is supplied.

The scanner considers every TIM magic candidate, validates the complete file
structure, and reports accepted images in source-offset order. Once it accepts
an image, it resumes at that image's end so a coincidental signature inside
pixel data cannot become a second overlapping result.

## Extract exact TIMs and PNG previews

```powershell
python tools/tim_tool.py extract `
  --source workspace/bns/entries/073.arc `
  --output workspace/textures/073 `
  --ids 0,2-4
```

Omit `--ids` to extract every accepted image. IDs are zero-based scan results
local to this exact source file; they are not global Tekken asset IDs. Filenames
also contain the stable source offset, for example:

```text
tim_0000_off_00001F58.tim
tim_0000_off_00001F58.p000.png
inventory.json
```

Indexed images export their first palette by default. Use `--all-palettes` to
write one `.pNNN.png` for every complete embedded palette. Direct-color images
produce one `.png`. Extraction preflights every requested path and refuses to
overwrite any of them unless `--force` is explicit. Writes use a temporary file
followed by an atomic replace.

## Supported standard TIM modes

| Mode | Validation and preview behavior |
|---|---|
| 4bpp | Requires one or more complete 16-color CLUTs; low nibble is the first pixel. |
| 8bpp | Requires one or more complete 256-color CLUTs. |
| 16bpp | Decodes PS1 5:5:5 RGB words and the STP bit. |
| 24bpp | Decodes complete `R,G,B` byte triplets in each 16-bit-word row. |

The PNG encoder writes deterministic, non-interlaced RGBA8 files. PS1 color
zero is shown as transparent. Because the hardware meaning of STP depends on
the active blend mode, previews use alpha 128 to make the bit visible; this is
not a promise of the exact in-game blend result. A 24bpp TIM has no explicit
pixel-width field, only a width in 16-bit VRAM words. The manifest reports the
maximum complete RGB pixels and `row_padding_bytes` (zero through two) rather
than treating an incomplete triplet as a pixel.

Strict validation requires:

- ordinary flags `0x08`, `0x09`, `0x02`, or `0x03`, with reserved bits clear;
- exact `12 + width_words * height * 2` section sizes and in-bounds data;
- nonzero dimensions and destinations inside 1024x512-word PS1 VRAM;
- whole 16- or 256-color palettes for indexed modes.

Mixed-depth, compressed, degenerate, malformed, oversized/custom, PXL, and CLT
variants are outside this tool's current contract. Rejecting those cases is
intentional: an inventory is more useful when random binary data is not
silently labeled as a texture.

## Inventory schema

`inventory.json` records the source path, byte size, SHA-256, scan policy, and
texture count. Each texture row contains:

- local scan `id`, source `offset`, `end_offset`, exact `size`, and SHA-256;
- flags, mode, bits per pixel, decoded width/height, and row padding;
- image and optional CLUT section/data offsets, sizes, dimensions, and VRAM
  destination coordinates;
- palette count and deterministic suggested artifact filenames;
- for extraction, the subset of artifact names actually written.

Offsets named `source_*` are absolute in the supplied binary. Other section
offsets are relative to the beginning of the extracted `.tim`.

## Strict local PNG import boundary

The companion [`tim_import.py`](TIM_IMPORT.md) can use an extracted standalone
TIM as an immutable layout contract and re-encode an identical-dimension RGBA
PNG. Its default indexed policy requires exact colors from one existing
palette. Explicit flags enable nearest mapping within that unchanged palette
or RGB555 quantization for 16bpp. Alpha/STP classes, supported PNG structure,
multi-palette rejection and direct-color rules are documented there.

The resulting exact-size `.tim` retains stock header/CLUT/layout bytes. It is a
private local derived staging artifact, not an independently authored or
automatically publishable release payload. A public mod can distribute only an
independently authored PNG/settings/recipe and regenerate from the user's
verified original locally; redistribute a rebuilt whole TIM only with
rightsholder permission or proof every redistributed byte is independently
authored. Neither `tim_tool.py` nor `tim_import.py` reinserts nested data or
accepts a PNG directly in `bns_mod.py`.

Run all tool tests with:

```powershell
python -m unittest discover -s tools/tests -v
```

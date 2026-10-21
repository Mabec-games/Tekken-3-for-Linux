# Numeric model structure maps

`model_map.py` is an original, standard-library-only, read-only mapper for two
model-like record profiles in the verified Tekken 3 USA `TEKKEN3.BNS`. It
produces deterministic JSON/CSV, entropy/hex navigation maps and bounded raw
section extracts. It does **not** convert a model, infer a skeleton, assign a
fighter/stage name or rebuild a record.

All output examples use `workspace/`, which is gitignored. Extracted sections
contain retail game data. Keep them private and do not publish, commit or ship
them with the project.

## Exact revision and numeric results

The mapper requires the same SHA-256-verified `SLUS-00402` executable as
`bns_tool.py`, then discovers `TEKKEN3.BNS` inside a raw/cooked Track 1 image
or accepts a standalone BNS file. A complete scan of the exact US archive
finds:

| Profile | Numeric records | What is actually proved |
|---|---:|---|
| `3dmk_observed_v1` | 52 | `3DMK` magic plus a bounded header, fixed-size row table and payload |
| `model_candidate_observed_v1` | 15 | A unique magic-free structural fingerprint, matched only by IDs `056` through `070` |

The second group is consistent with the suspected stage-model record range,
but the file has no name or magic proving a stage identity. The public schema
therefore says `model_candidate`, leaves `semantic_name` null and never emits
guessed stage names.

## Inventory

```powershell
python tools/model_map.py inventory `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --json workspace/models/model-map.json `
  --csv workspace/models/sections.csv
```

With neither `--json` nor `--csv`, JSON is written to standard output. The
tool preserves existing requested outputs unless `--force` is supplied.

The JSON records the verified executable/table/source identity, one numeric
BNS ID per model record, hashes and byte metrics for every major section, raw
row words, validated or candidate relative offsets, 256-byte entropy blocks
and short eight-byte hex prefixes. The CSV is deliberately flatter: one row
per major raw section with its ID, range, SHA-256 and byte metrics.

Entropy and printable/zero fractions are browsing aids. They do not identify
vertices, polygons, animation data or compression.

## Raw section extraction

```powershell
python tools/model_map.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output workspace/models/sections `
  --ids 56,71
```

Omit `--ids` to extract every record matching either strict profile. Paths are
numeric and deterministic:

```text
workspace/models/sections/
  model_map.json
  sections.csv
  056/
    section_000_header.bin
    section_001_row_table.bin
    section_002_variable_stream.bin
    section_003_fixed_stride8_stream.bin
  071/
    section_000_header.bin
    section_001_row_table.bin
    section_002_payload.bin
```

The sections are exact, non-overlapping and cover each selected record. They
are visibility/research slices, not independently loadable assets.

## `3dmk_observed_v1` envelope

The following layout is validated without assigning meanings to the payload:

| Offset | Structural field |
|---:|---|
| `0x00` | little-endian row count |
| `0x04` | unknown `u32` |
| `0x08` | ASCII `3DMK` |
| `0x0C` | observed zero `u32` |
| `0x10` | payload relative offset, using byte `8` as the base |
| `0x14` | observed zero `u32` |
| `0x18` | start of `row_count` rows, 56 bytes / 14 `u32` words each |

`8 + payload_relative_offset` must equal
`24 + row_count * 56` exactly and remain inside the record. The mapper then
splits `header`, `row_table` and the remaining `payload`.

Across all 52 verified US records, nonzero row words `0`, `1`, `2` and `13`
are aligned in-payload relative offsets. Word `12` is either zero, the small
value `2`, or another aligned in-payload relative offset. Their exact
semantics are not proved. JSON calls them observed offset columns and creates
candidate intervals between their distinct targets only as navigation aids;
those intervals are not asserted model sections.

Every other row word remains an opaque integer except for structural profile
checks (observed boolean word `10` and zero word `11`). In particular, the
tool does not label rows as bones or any offsets as vertex/animation tables.

## `model_candidate_observed_v1` envelope

This no-magic fingerprint is stricter because it must not misclassify arbitrary
`BIN` records:

| Offset | Structural field |
|---:|---|
| `0x00` | opaque `u32`, observed value `65` |
| `0x04` | opaque `u32` |
| `0x08` | row count, observed value `36` |
| `0x0C` | start of 36 rows, 28 bytes / seven `u32` words each |

All stored offsets in this profile are relative to byte `12`. For every row:

- word `0` is a relative offset into the final stream;
- word `1` is a count, and `count * 8` reaches the next row's word-0 offset;
- the 36 word-0/count ranges are contiguous and end exactly at EOF;
- word `2` is an EOF-relative marker in the first row and zero thereafter;
- words `3` and `5` contain the same opaque value;
- word `4` is an aligned, bounded, monotonic offset into the preceding stream;
- word `6` is zero.

The first word-4 target exactly follows the row table. The first word-0 target
therefore divides the remaining bytes into a bounded `variable_stream` and an
exact `fixed_stride8_stream`. The word-4 spans are shown using the next
distinct offset, but the duplicate opaque value is **not** interpreted as a
byte count: some real records demonstrate that a fixed-size assumption would
be false.

These relationships reliably distinguish all fifteen records from the other
288 entries in the exact US BNS. They still do not prove that an individual ID
belongs to any named stage or what either stream contains.

## Safety boundary

- Source files are opened read-only. The executable, BNS and BIN/CUE are never
  rewritten.
- Every table, offset and derived range receives strict overflow/bounds/order
  checks before it is reported or extracted.
- A malformed `3DMK` marker is an error. A no-magic near-match is ignored
  unless the complete fingerprint validates.
- Existing outputs are preserved without `--force`; writes use a temporary
  file followed by an atomic replace.
- This is not an importer or repacker. Use numeric BNS whole-record overlays
  only after independently authoring and validating an exact-size replacement.

Run the synthetic regression suite with:

```powershell
python -m unittest tools.tests.test_model_map -v
```


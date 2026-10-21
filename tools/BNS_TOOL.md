# Local BNS inventory and extraction

`bns_tool.py` inventories and extracts the 303 numeric records in the US
`TEKKEN3.BNS` file. It is an original, standard-library-only Python tool. It
does not invoke or require an external extractor.

The tool never modifies the executable, BNS archive, or disc image. Outputs go
under the gitignored `workspace/` directory in these examples. They contain
copyrighted game data and must remain local: do not commit, publish, or include
them in a release.

## Supported game

Only **Tekken 3 (USA), SLUS-00402** is supported. The tool verifies the
executable by SHA-256 before using its table:

| Property | Value |
|---|---:|
| Executable SHA-256 | `fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c` |
| Table virtual address | `0x80024400` |
| Table file offset | `0x14C00` |
| Entry count | 303 |
| Entry layout | little-endian `{ u32 sector, u32 size }` |

`sector` is relative to the start of `TEKKEN3.BNS`, in 2048-byte logical
sectors. It is not an absolute disc LBA. IDs are fixed, zero-based table
indices from `0` through `302` for this release.

## Inventory

Use either the standalone archive:

```powershell
python tools/bns_tool.py inventory `
  --exe disc/SLUS_004.02 `
  --source disc/TEKKEN3.BNS `
  --json workspace/bns/inventory.json `
  --csv workspace/bns/inventory.csv
```

Or point the same command at the raw data track. The ISO 9660 record for
`/TEKKEN3/TEKKEN3.BNS;1` is located automatically; its physical LBA is not
hard-coded:

```powershell
python tools/bns_tool.py inventory `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --json workspace/bns/inventory.json `
  --csv workspace/bns/inventory.csv
```

If neither `--json` nor `--csv` is supplied, JSON is written to standard
output. Existing requested output files are preserved unless `--force` is
explicitly supplied.

Each inventory row contains:

- `id`: stable US table index, `0` to `302`.
- `sector`, `offset`, `size`, and `end_offset`: BNS-relative locations.
- `sha256`: hash of the exact unpadded entry bytes. Empty records receive the
  standard SHA-256 of an empty byte string.
- `kind` and `extension`: conservative signature hints.
- `suggested_filename`: a zero-padded numeric name such as `071.3dm`.

The JSON document also records source/container details and hashes the
executable and raw 2,424-byte table. The CSV contains one flat row per entry.

## Extraction

Extract a small selection with comma-separated IDs and inclusive ranges:

```powershell
python tools/bns_tool.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output workspace/bns/entries `
  --ids 71,72-74
```

Omit `--ids` to extract every record. Payload files use numeric, zero-padded
names (`000` through `302`) plus the conservative extension. Zero-size records
stay in both inventories but do not create payload files. Extraction always
writes `inventory.json` and `inventory.csv` beside the selected payloads.

The tool preflights matching outputs and refuses to overwrite them unless
`--force` is used. Writes use a temporary file followed by an atomic replace.

## Signature hints

Classification is intentionally narrow and is not a promise that a complete
parser exists:

- `3DMK` requires the `3DMK` marker at byte offset 8 and suggests `.3dm`.
- `VH`/`VAB` requires the PlayStation `pBAV` header and uses its declared total
  size to distinguish a header-only entry from a complete bank.
- `ARC` requires a plausible count plus a contiguous, in-bounds offset/size
  directory that consumes the record exactly.
- `TIM` requires a valid TIM mode and structurally consistent CLUT/image block
  lengths and dimensions.
- Everything else remains `BIN`; a `BIN` result means unknown, not invalid.

These hints are suitable for browsing and choosing research targets. They must
not be used as the only validation before editing or repacking an asset.

## Current boundary

This utility provides read-only inventory and extraction. It does not repack
`TEKKEN3.BNS`, rewrite the executable table, build a disc image, or alter the
retail track. BNS-relative `sector * 2048` is not a raw Track 1 byte offset
because raw sectors contain framing and error-correction bytes.

For records conservatively classified as `ARC`, `arc_tool.py` provides a
separate strict member inventory/extract/rebuild workflow. It operates only on
an extracted record in the local workspace and does not change this tool's
read-only disc boundary. `bns_mod.py --arc-replacement` can then package only
an exact-size authored member without copying retail siblings. See
`ARC_TOOL.md`.

For an exact-size author-owned record replacement, the companion
`bns_mod.py` builder combines the discovered BNS ISO extent with that relative
sector and emits a guarded PSXRecomp `disc_user` overlay. See `BNS_MOD.md` for
the supported package workflow and its revision, size, and copyright checks.

To locate and preview strict standard PS1 TIM images inside one of the locally
extracted records, use the read-only companion `tim_tool.py`. Its source-local
ID/offset schema, PNG behavior, and limitations are documented in
`TIM_TOOL.md`.

To map the strict structural envelopes of the 52 `3DMK` records and 15
no-magic model candidates without assigning guessed character/stage names,
use `model_map.py`. It emits numeric JSON/CSV, entropy blocks and bounded raw
section extracts as documented in `MODEL_MAP.md`.

For the 48 split PlayStation sound banks, `vab_tool.py` strictly proves each
known VH/ARC relationship and reconstructs a conventional `.vab` from the VH
record plus ARC member 2. It requires both verified numeric IDs and never
modifies the retail source. See `VAB_TOOL.md`.

Run the tests with:

```powershell
python -m unittest discover -s tools/tests -v
```

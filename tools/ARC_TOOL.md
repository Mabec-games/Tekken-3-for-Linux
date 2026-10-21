# Tekken 3 BNS ARC workspace tool

`arc_tool.py` validates, inventories, extracts and locally rebuilds the strict
ARC containers found in top-level `TEKKEN3.BNS` records. It uses only the
Python standard library and operates on one record previously extracted with
`bns_tool.py`. It never edits `TEKKEN3.BNS`, a BIN/CUE or an executable.

## Accepted ARC contract

The verified Tekken 3 (USA) ARC records use this compact layout:

```text
u32 little-endian member_count
member_count * { u32 offset, u32 size }
0-15 bytes of 0xFF directory padding
contiguous member spans
```

The parser fails closed unless the count is `1..255`, every member offset and
size is four-byte aligned, the first member follows the directory and its
small padding, every later offset equals the previous end, and the final end
equals the ARC file size. Zero-size members are supported. Numeric member IDs
are zero-based directory indexes and are meaningful only together with the
stock top-level BNS record ID and hash.

These checks intentionally describe only the ARC envelope. A `TIM_MAGIC`,
`VAB_MAGIC` or `3DMK_MAGIC` inventory value is a browsing hint based on a few
magic bytes, not proof that the complete member is valid or understood.

## Inventory and extraction

First extract an ARC top-level record into a gitignored workspace:

```powershell
python tools/bns_tool.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output out/bns/record-073 `
  --ids 73
```

Validate and catalog it:

```powershell
python tools/arc_tool.py inventory `
  --input out/bns/record-073/073.arc `
  --json out/bns/record-073/arc-inventory.json `
  --csv out/bns/record-073/arc-inventory.csv
```

Extract all members, or select a stable numeric range with `--ids 0,2-4`:

```powershell
python tools/arc_tool.py extract `
  --input out/bns/record-073/073.arc `
  --output out/bns/record-073/members
```

Extraction writes constructed names such as `000.bin` and `001.tim` plus
`arc_manifest.json`. The manifest is deterministic and path-independent: it
records the ARC size/hash, layout, member offsets/sizes/hashes, conservative
magic hints and the selected IDs, but no timestamps or source paths. Existing
outputs are refused unless `--force` is explicit.

## Exact-size local rebuild

The default rebuild mode is useful for local format validation and testing. A
replacement must have exactly the stock member size and be four-byte aligned:

```powershell
python tools/arc_tool.py rebuild `
  --input out/bns/record-073/073.arc `
  --replacement "1=mods/workspace/my-pack/member-001.bin" `
  --output out/bns/record-073/073-rebuilt.arc `
  --report out/bns/record-073/073-rebuild.json
```

The tool preserves the member count, source directory padding and all
unmodified member bytes, rewrites the complete directory deterministically,
and validates its own result. The optional report contains only sizes and
hashes. It says `exact_top_level_size: true` when the rebuilt ARC can pass the
current `bns_mod.py` top-level size policy. The rebuilt file still contains
unchanged retail members, so keep it private even though its layout is valid.

## Publishable exact-size member package

Do not package the rebuilt whole ARC for ordinary distribution: that would
copy every unchanged retail member into the mod. Instead, let `bns_mod.py`
locate and hash the member directly on the player's verified disc, and package
only the independently authored exact-size payload:

```powershell
python tools/bns_mod.py `
  --package-id example.arc-pack `
  --version 1.0.0 `
  --name "Example ARC Pack" `
  --author "Mod Author" `
  --arc-replacement "073:1=mods/workspace/my-pack/member-001.bin" `
  --output out/example-arc-pack-1.0.0 `
  --archive out/example-arc-pack-1.0.0.psxmod
```

`bns_mod.py` verifies the exact US disc, validates top-level record 073 as a
strict ARC, requires the authored file to match member 1's stock size, and
guards that precise stock member range by SHA-256. The package contains only
the supplied member file and a default-off `disc_user` overlay; the ARC
directory and sibling retail members remain on the player's disc. Neither
tool modifies the original disc.

## Intentional resized rebuilds

`--allow-resize` permits local member sizes to change and rewrites all following
offsets. Resized payloads still must be four-byte aligned; the tool never adds
ambiguous padding silently. The release-safe `--arc-replacement` adapter does
not accept resized members because it intentionally leaves the stock ARC
directory and sibling ranges untouched. Even when local growth and shrinkage
balance to the original outer size, publishing the whole rebuilt ARC would
redistribute unchanged retail bytes. A release-safe relocated/resized design
requires separate directory patches plus a loader strategy and is not
implemented.

## Local-data boundary

An extracted ARC, its members and a rebuilt ARC contain retail bytes. Keep
them under ignored `out/` or `mods/workspace/` paths and do not commit or
publish them. A distributable `.psxmod` may contain only independently
authored replacement material for which the author has redistribution rights.

Run all tool tests with:

```powershell
python -m unittest discover -s tools/tests -v
```

# Guarded BNS mod package builder

`bns_mod.py` converts one or more exact-size, author-owned BNS record or strict
ARC-member replacements into a PSXRecomp package source and, optionally, a
deterministic `.psxmod` archive. It never writes to the BIN/CUE or repacks
`TEKKEN3.BNS`.

The builder supports only the verified US retail data track (`SLUS-00402`). It
hashes the complete raw Track 1 and requires:

| Property | Required value |
|---|---:|
| Track 1 size | `632532768` bytes |
| Track 1 SHA-256 | `6b660e62748d02779e9e08362a5ed202540af7fad134de2ec0a2184ad78bb496` |
| Executable SHA-256 | `fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c` |

## Build a package

Supply each complete-record replacement as a repeated numeric `ID=FILE`
argument:

```powershell
python tools/bns_mod.py `
  --package-id example.my-bns-pack `
  --version 1.0.0 `
  --name "My BNS Pack" `
  --author "Mod Author" `
  --license CC-BY-4.0 `
  --replacement "071=mods/workspace/my-pack/071.bin" `
  --replacement "074=mods/workspace/my-pack/074.bin" `
  --output "out/my-bns-pack-1.0.0" `
  --archive "out/my-bns-pack-1.0.0.psxmod"
```

The default input paths are `disc/SLUS_004.02` and
`disc/Tekken 3 (USA) (Track 1).bin`. Use `--exe` and `--track` only when those
verified files live elsewhere.

`--output` must name a new package source directory. `--archive` is optional
and must name a new `.psxmod` file outside that directory. Existing outputs are
never overwritten.

For a member inside a strict ARC record, use the release-safe
`BNS_ID:MEMBER=FILE` form instead. It packages only the authored member, not a
rebuilt container containing retail siblings:

```powershell
python tools/bns_mod.py `
  --package-id example.arc-pack `
  --version 1.0.0 `
  --name "Example ARC Pack" `
  --author "Mod Author" `
  --arc-replacement "073:1=mods/workspace/my-pack/member-001.bin" `
  --output "out/example-arc-pack-1.0.0" `
  --archive "out/example-arc-pack-1.0.0.psxmod"
```

The two options can be repeated and combined for different top-level records.
A complete `--replacement 073=...` and an `--arc-replacement 073:...` cannot
coexist because their overlay ranges would overlap.

## Validation and generated operations

The builder reuses `bns_tool.py` to verify the executable table, discover
`/TEKKEN3/TEKKEN3.BNS;1` from ISO 9660, and inventory the stock records. For
each complete selected ID it requires a non-empty replacement with exactly the
stock record's unpadded byte size and emits feature `bns-NNN`. For an ARC
selector it additionally validates the strict container from the verified
disc, requires the exact non-empty member size, and emits feature
`bns-NNN-arc-MMM`. Every feature is independently selectable and default-off.

Each generated overlay contains:

- `target = "disc_user"`;
- the record offset `(bns_iso_extent_lba + record_sector) * 2048`, plus the
  validated member offset for an ARC member;
- the SHA-256 of the copied replacement payload;
- `expected_sha256` for the precise complete-record or member stock range; and
- a constructed safe path such as `assets/bns/071.bin` or
  `assets/bns/073/arc/001.bin`.

The package target also pins `game_id`, executable SHA-256, and complete data
Track 1 SHA-256. A wrong revision or changed stock range therefore fails
closed before the overlay is used. The original disc stays byte-identical;
disabling the feature removes the overlay.

This narrow workflow intentionally does not resize or relocate records, edit
the executable table, patch XA/STR streams, or rebuild a disc image. A shorter
payload is not padded automatically because silent padding can corrupt formats
whose internal lengths must be authored deliberately.

## Packaging a strict ARC member

For a top-level entry classified as `ARC`, use `arc_tool.py` to inventory and
locally test numeric members. For distribution, pass the independently
authored member directly to `--arc-replacement`:

```powershell
python tools/arc_tool.py rebuild `
  --input out/bns/record-073/073.arc `
  --replacement "1=mods/workspace/my-pack/member-001.bin" `
  --output out/bns/record-073/073-rebuilt.arc `
  --report out/bns/record-073/073-rebuild.json

python tools/bns_mod.py `
  --package-id example.arc-pack `
  --version 1.0.0 `
  --name "Example ARC Pack" `
  --author "Mod Author" `
  --arc-replacement "073:1=mods/workspace/my-pack/member-001.bin" `
  --output out/example-arc-pack-1.0.0 `
  --archive out/example-arc-pack-1.0.0.psxmod
```

The builder reads the stock ARC only from the verified local disc, validates
its strict envelope, computes the precise member `disc_user` offset and
`expected_sha256`, and copies only the supplied member into the package. ARC
member sizes must remain exact. A locally rebuilt ARC contains unchanged
retail siblings and must not be used as a distributable whole-record payload.
See `ARC_TOOL.md` for the strict format contract and resized local-test mode.

## Publishing responsibility

The package source and `.psxmod` archive contain the replacement files passed
on the command line. The tool cannot prove who authored them. Only distribute
a package when you have redistribution rights to every replacement. Never use
an extracted or byte-identical retail record as a published replacement; keep
such records and validation packages temporary and local.

Run all focused tooling tests with:

```powershell
python -m unittest discover -s tools/tests -v
```

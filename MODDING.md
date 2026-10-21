# Tekken 3 Recompiled modding guide

This document describes the currently verified Tekken 3 (USA,
`SLUS-00402`) asset namespaces and the mod paths that the runtime supports
today. It also reserves a proposed loose-override layout for future tools.

The guiding rule is simple: keep the player's original disc immutable. A mod
is a small, reviewable package applied over a verified local disc at launch.

## Project status

The PC runtime boots and plays through static recompilation plus the
PSXRecomp compatibility paths. This is an early reverse-engineering build,
not a complete source-code recreation. Names and meanings that have not been
proved are intentionally left as numeric IDs.

The launcher and runtime support PSXRecomp `.psxmod` packages now. The narrow
Tekken-specific `bns_mod.py` adapter builds exact-size numeric BNS replacements
as guarded `disc_user` overlays. The companion `arc_tool.py` now exposes strict
numeric member inventory, extraction and deterministic rebuilds for the 75
top-level records classified as ARC; `bns_mod.py --arc-replacement` packages
only an authored exact-size member rather than its retail siblings. More
semantic operations and resized members/outer records still require future
adapters or carefully authored generic package operations. The separate
`xas_mod.py` adapter covers exact-budget, already encoded XA/STR media.

## Supported retail revision

All offsets and IDs in this document refer only to the US retail revision.

| Item | Verified value |
|---|---|
| Game ID | `SLUS-00402` |
| Volume | `TEKKEN3` |
| Boot executable | `SLUS_004.02` |
| Executable SHA-256 | `fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c` |
| Data Track 1 size | `632532768` bytes |
| Data Track 1 SHA-256 | `6b660e62748d02779e9e08362a5ed202540af7fad134de2ec0a2184ad78bb496` |
| Track count | 3 (one data track and two CD-audio tracks) |
| TOC fingerprint | `d6179326b7eaaccf6de7e1f6bda382be57ee87221f9425dc9401639171f56c19` |

The full identity record lives in `catalog_identity.json`. Reject a different
revision instead of trying to apply these offsets to it.

## Verified disc map

The ISO filesystem contains these important files under `TEKKEN3/`:

| File | LBA | Byte size | Purpose/status |
|---|---:|---:|---|
| `SLUS_004.02` | 25 | 1,185,792 | PS-X EXE; load `0x80010000`, entry `0x80079C70` |
| `TEKKEN3.XAS` | 604 | 511,082,496 | Mixed XA audio and STR/MDEC movie sectors |
| `TEKKEN3.BNS` | 250156 | 38,150,144 | Main indexed asset bank |
| `TEKKEN3.DA` | 269084 | 23,814,144 | Filesystem extent into audio Track 2 |
| `TEKKEN3.DMY` | 280862 | 24,111,104 | Filesystem extent into silent audio Track 3 |

`TEKKEN3.DA` and `TEKKEN3.DMY` are not ordinary 2048-byte ISO data files. Preserve the
three-track BIN/CUE layout when testing audio or rebuilding media.

## Stable asset IDs

### BNS records

The boot executable contains a table of exactly 303 records at executable
file offset `0x14c00`, guest address `0x80024400`. Each record is:

```text
u32 little-endian sector
u32 little-endian byte_size
```

The stable asset ID is the zero-based table index, `0` through `302`. Use the
zero-padded spelling `000` through `302` in filenames. These IDs are stable for
the supported US executable; names such as a character or stage are aliases
only after they have been demonstrated in game. Do not infer them from record
order.

The current `bns_tool.py` conservative signature classifier reports:

| Detected kind | Count |
|---|---:|
| `3DMK` records | 52 |
| PlayStation VAB header (`VH`) records | 48 |
| Strict ARC containers | 75 |
| Unknown binary (`BIN`) records | 122 |
| Empty records | 6 |

Provisional internal research scans found thousands of TIM-like signatures and
tentative subgroups inside the `BIN`/ARC population. Those are exploration
results, not extra top-level kinds or proved independent textures. The checked-in
`tim_tool.py` now provides a stricter per-record scanner: it validates complete
standard TIM structures, assigns source-local numeric IDs and offsets, and can
export exact `.tim` payloads plus PNG previews without external dependencies.

Create a local machine-readable catalog with:

```powershell
python tools/bns_tool.py inventory `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --json out/bns/inventory.json `
  --csv out/bns/inventory.csv
```

To produce one path-independent, payload-free metadata catalog across BNS,
VAB, model, XA, and STR analyzers instead, run:

```powershell
python tools/catalog_assets.py `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output out/catalog/assets.json
```

See `tools/CATALOG_ASSETS.md` for its deterministic schema and strict
no-retail-payload boundary.

Extract selected records without committing them:

```powershell
python tools/bns_tool.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output out/bns/entries `
  --ids 71,72-74
```

Omit `--ids` to extract all non-empty records. The JSON catalog records each
ID's BNS-relative 2048-byte sector, BNS byte offset, exact unpadded byte size, SHA-256
and conservative detected kind. Keep IDs numeric in manifests even when a
local notes file supplies a friendlier alias. Do not hand-convert the relative
sector into a raw Track 1 byte offset. Use `bns_mod.py`, which verifies the
revision and accounts for the discovered BNS ISO extent.

See `tools/BNS_TOOL.md` for the complete output schema, overwrite rules and
classification checks. Inventory and extraction are deliberately read-only;
the tool does not repack the bank or modify the disc.

Build a numeric, conservative structure map of every strict `3DMK` record and
the distinct no-magic model-candidate profile, or extract only their bounded
raw sections:

```powershell
python tools/model_map.py inventory `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --json out/models/model-map.json `
  --csv out/models/sections.csv

python tools/model_map.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output out/models/sections `
  --ids 56,71
```

The verified scan yields 52 magic-bearing `3DMK` records and 15 no-magic
records whose complete offset/row/stream fingerprint is unique in the US BNS.
Those 15 numeric IDs are consistent with the suspected stage-model range, but
the format does not prove stage names; the tool reports `semantic_name = null`.
It exposes exact major byte ranges and candidate offset intervals, not a model
import or editable skeleton. See `tools/MODEL_MAP.md` for the proved fields,
unknown-word policy and extraction schema.

Scan an extracted record for standard 4/8/16/24bpp TIM images and preview a
selected range locally:

```powershell
python tools/tim_tool.py inventory `
  --source out/bns/entries/073.arc `
  --json out/textures/073-inventory.json

python tools/tim_tool.py extract `
  --source out/bns/entries/073.arc `
  --output out/textures/073 `
  --ids 0-4
```

TIM scan IDs are local to the exact supplied record; retain its source offset
and SHA-256 when taking notes. See `tools/TIM_TOOL.md` for strict validation,
multiple-palette previews, transparency conventions and the editing boundary.
`tim_import.py` can re-encode a same-dimension RGBA PNG into one standalone
TIM while preserving its exact layout and size. It requires explicit
palette/STP-safe policies and does not update its containing ARC/BNS record:

```powershell
python tools/tim_import.py `
  --original out/textures/073/tim_0000_off_00000000.tim `
  --png mods/workspace/my-pack/texture.png `
  --output mods/workspace/my-pack/texture.tim `
  --report mods/workspace/my-pack/texture-report.json
```

See `tools/TIM_IMPORT.md` for accepted PNGs and color rules. The rebuilt TIM
retains stock layout and possibly stock bytes, so keep it as a private derived
staging artifact. A public mod should distribute its authored PNG/settings and
regenerate against each user's verified original unless the author has rights
to every byte shipped. Neither PNG nor nested TIM is accepted directly by
`bns_mod.py`; reinserting it into the containing record remains a separate
exact-layout step.

Build a guarded package from one or more exact-size author-owned records:

```powershell
python tools/bns_mod.py `
  --package-id example.my-pack `
  --version 1.0.0 `
  --name "My BNS Pack" `
  --author "Mod Author" `
  --replacement "071=mods/workspace/my-pack/071.bin" `
  --output "out/my-pack-1.0.0" `
  --archive "out/my-pack-1.0.0.psxmod"
```

See `tools/BNS_MOD.md` for the exact contract and publishing boundary.

For an extracted top-level record classified as `ARC`, inventory or extract
its zero-based members without assigning guessed semantic names:

```powershell
python tools/arc_tool.py inventory `
  --input out/bns/entries/073.arc `
  --json out/bns/entries/073-arc.json

python tools/arc_tool.py extract `
  --input out/bns/entries/073.arc `
  --output out/bns/arc-073-members
```

Rebuild an exact-size member locally for format testing:

```powershell
python tools/arc_tool.py rebuild `
  --input out/bns/entries/073.arc `
  --replacement "1=mods/workspace/my-pack/member-001.bin" `
  --output out/bns/entries/073-rebuilt.arc
```

That complete rebuilt ARC is a private local oracle only; do not pass it to a
distributable whole-record package because it contains unchanged retail
members.

For a distributable package, give only the independently authored member to
the guarded adapter so unchanged retail siblings are not copied:

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

See `tools/ARC_TOOL.md` for the accepted envelope, deterministic manifest,
resized-member policy and full packaging example. Magic hints in an ARC
inventory are browsing aids, not semantic asset validation.

### XAS media

The checked-in `xas_tool.py` turns the XAS research into a strict, reproducible
read-only catalog for the verified US Track 1. The executable's table begins at
file offset `0x15578` and contains 50 standalone XA descriptors. Their stable
ID is the zero-based table row, `0` through `49`; keep it numeric rather than
publishing guessed movie, song, voice or character labels.

Each descriptor stores an eight-sector-aligned start group, inclusive end
group and XA channel. The selected raw sectors are `start + channel` through
`end + channel`, inclusive, with stride 8. The tool proves file number 1,
the table channel, coding `0x01`, ordinary submode `0x64` and one terminal
`0xE4` EOF sector for every row.

The same complete sector scan derives 22 numeric STR movie-region IDs in
ascending order. Regions begin only at a validated chunk-0/frame-1 reset and
include every raw sector from their first through last STR sector, preserving
interleaved XA channel 1 and padding. All 111,099 STR sectors have valid
magic/type, complete ordered chunks, contiguous frame numbers and consistent
per-frame metadata. These movie IDs are scan positions for this exact revision,
not semantic names.

Generate the deterministic JSON/CSV catalog locally:

```powershell
python tools/xas_tool.py inventory `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --json out/xas/inventory.json `
  --csv out/xas/inventory.csv
```

Selected exact raw-sector streams can be emitted to the ignored workspace for
format research:

```powershell
python tools/xas_tool.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output out/xas/streams `
  --xa-ids 0,4-6 `
  --movie-ids 0,21
```

See `tools/XAS_TOOL.md` for the exact schema, hashes, boundary proof and
extraction format. The outputs contain retail media and must not be committed
or distributed.

Replacement XA/STR media must fit the original sector budget unless a future
loader explicitly relocates it. The guarded `xas_mod.py` adapter now accepts
already encoded author-owned raw sectors, validates sector framing, EDC/ECC,
file/channel/coding, audio interleave and STR frame/chunk structure, and emits
default-off format-6 `disc_raw` overlays. It stores only sector bodies, so
absolute sync/MSF/mode headers remain stock; eight-way XA sibling channels are
gaps rather than package data or writes. See `tools/XAS_MOD.md`.

## Mod workflow supported today

### 1. Work only from a clean local disc

Put the verified BIN/CUE files in the gitignored `disc/` directory. Run the
inventory tools against those files and keep extraction output under a
gitignored working directory such as `out/`.

Never edit the stock BIN in place. Preserve it as the comparison oracle and
make every mod reversible.

### 2. Choose the narrowest operation

| Change | Current mechanism |
|---|---|
| Fixed executable code or data | Guarded `[[patch]]` with `target = "main_exe"` |
| A few disc bytes | Guarded `[[patch]]` on `disc_raw` or `disc_user` |
| Exact-size numeric BNS record | `bns_mod.py` generated guarded `disc_user` overlay |
| Exact-size member inside a strict BNS ARC record | `bns_mod.py --arc-replacement` guarded member overlay |
| Encoded XA stream or STR movie span | `xas_mod.py` guarded strided `disc_raw` overlay |
| Other texture, model, sound or movie payload | File-backed, SHA-256-guarded `[[overlay]]` |
| Host-side or per-VBlank behavior | Reviewed static plugin compiled into this project |

`main_exe` patch addresses are PS1 guest virtual addresses. Every patch must
provide the complete stock `expected` bytes and fails closed if they differ.

Disc offsets use the runtime's canonical coordinate systems:

```text
disc_raw  = lba * 2352 + byte_in_raw_sector
disc_user = lba * 2048 + byte_in_user_sector
```

Small patches cannot cross a sector. File-backed overlays can span sectors,
but must include a payload SHA-256 and should include `expected_sha256` for the
stock range. For complete BNS records, `bns_mod.py` computes
`(bns_extent_lba + record_sector) * 2048`, requires the exact original unpadded
size and guards the entire stock range. For `--arc-replacement`, it adds the
strictly parsed member offset, requires that member's exact size and guards
only that precise stock range, so the package contains no retail siblings. It
never pads a shorter file. Changing the table size or relocating data requires
a separately guarded executable patch and dedicated testing; it is not
supported by the BNS package builder.

The complete package schema is in `psxrecomp/docs/MOD_PACKAGES.md`. The inert
example at `mods/examples/noop/manifest.toml` is safe to copy as a starting
point because it contains no game bytes and performs no writes.

### 3. Package and install

```powershell
python psxrecomp/tools/psxmod_pack.py `
  mods/examples/noop `
  out/example-noop-1.0.0.psxmod
```

Install the archive through the launcher's Mods manager. The release packager
can stage reviewed built-in package sources from this layout:

```text
mods/preloaded/packages/<package-id>/<version>/
  manifest.toml
  assets/
```

The current top-level `CMakeLists.txt` does not copy that directory into an
ordinary local `build-release` tree. Use the launcher to install local test
archives; do not mistake a source placed under `mods/preloaded` for an active
mod in that build.

Every feature should default to off until its all-off identity, wrong-revision
rejection, enabled behavior and save compatibility have been tested.

## Proposed loose override workspace

This is a reserved authoring layout, not a runtime promise yet:

```text
mods/workspace/<package-id>/
  manifest.toml
  README.md
  aliases.toml                 # optional human labels; numeric IDs stay canonical
  overrides/
    bns/
      071/
        asset.toml             # id, stock SHA-256, size policy, notes
        payload.dat            # author-owned replacement record
      073/
        arc/
          001/
            asset.toml         # BNS ID, ARC member ID, stock range hash/size
            payload.dat        # author-owned exact-size member only
    xas/
      <range-id>/
        asset.toml             # stock range, coding parameters, sector budget
        payload.dat
  build/                       # generated package source; never commit retail bytes
```

The current `bns_mod.py` adapter covers exact-size top-level BNS records and
exact-size strict ARC members, while `arc_tool.py` can deterministically
rebuild those ARC records for local testing. A future richer workspace adapter
can translate other nested or semantic entries into ordinary guarded
PSXRecomp overlays. XAS media packaging is implemented separately by
`xas_mod.py`; these adapter contracts should remain:

- `bns/<id>` always means the zero-based US table ID, never a guessed name;
- every replacement pins its precise stock range SHA-256, exact byte size and span;
- XAS replacements pin the stock logical sector chunks, count, channel/coding
  mode, complete disc hash, and precise stock chunk hash;
- conversion is deterministic and produces no modified disc image;
- `build/` contains only generated local output and is gitignored;
- unknown fields fail validation instead of being silently ignored.

Until a richer workspace adapter exists, `mods/workspace` is also the local
authoring area for ARC member payloads and nested/XAS notes. Use `arc_tool.py`
for complete local ARC validation, but let `bns_mod.py --arc-replacement`
generate the release operation directly from the authored member so no retail
sibling data enters the package. Otherwise put operations explicitly in the
package's `manifest.toml`.

## Testing checklist

For each feature:

1. Verify the clean US disc and record its stock range hash.
2. Test with every other feature off.
3. Confirm disabling the feature restores byte-identical vanilla reads.
4. Confirm a wrong executable/disc hash fails before boot.
5. Test representative feature combinations and inspect collision diagnostics.
6. Test a complete match, replay/demo paths, both players and save/load where
   the changed asset can appear.
7. Compare timing, video and audio with the original game in DuckStation.

DuckStation is a behavioral oracle, not a component of the shipped runtime.
Do not copy its code, BIOS files, shader cache, captures or configuration into
a release.

## Release and copyright policy

Tekken 3 and its retail data belong to their respective rights holders. This
repository can contain original tooling, documentation, empty schemas and
independently authored replacement assets with a clear license. It must not
contain or distribute:

- BIN/CUE/ISO/CHD files, BIOS dumps or memory cards;
- files extracted from `BNS`, `TEKKEN3.XAS` or the retail executable;
- modified disc images or prepatched game data;
- generated recompiler output under `generated/`;
- a compiled executable containing generated retail game code;
- screenshots, audio or other game media unless their use has been separately
  reviewed and permitted.

Public builds should require each player to supply and verify their own legal
disc, then generate the game-derived code and assets locally. Mod authors must
also have redistribution rights for every replacement they publish.

PSXRecomp is presently licensed under the PolyForm Noncommercial License
1.0.0. Commercial use requires a separate license or another suitably licensed
runtime, in addition to any permissions required for Tekken 3 itself. This is
an engineering release policy, not legal advice.

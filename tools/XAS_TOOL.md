# Local XAS inventory and extraction

`xas_tool.py` catalogs the XA audio streams and STR movie regions in the US
`TEKKEN3.XAS` file. It is an original, Python-standard-library-only, read-only
tool. It does not decode audio/video, patch a disc, or assign guessed media
names.

The only supported input is the exact raw 2352-byte Mode 2 Track 1 for Tekken
3 (USA), `SLUS-00402`. Both the executable and complete data track are verified
by SHA-256 before the ISO record is used. Extracted streams are retail data and
must stay in the gitignored `workspace/` or `out/` directories.

## Verified source

| Property | Value |
|---|---:|
| Executable SHA-256 | `fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c` |
| Track 1 size | `632532768` bytes |
| Track 1 SHA-256 | `6b660e62748d02779e9e08362a5ed202540af7fad134de2ec0a2184ad78bb496` |
| XAS ISO path | `/TEKKEN3/TEKKEN3.XAS;1` |
| XAS extent | LBA `604`, 249,552 sectors |
| XAS logical size | `511082496` bytes |
| Raw XAS span SHA-256 | `78cbc376c9031a47285362b3d3ee38207c6af21066ecde699e9958a01ecb09a5` |

The XAS descriptor table begins at executable file offset `0x15578` and has
exactly 50 rows:

```text
u32 little-endian start_group_sector
u32 little-endian end_group_sector
u32 little-endian XA_channel
```

`start_group_sector` and `end_group_sector` are XAS-relative bases aligned to
eight sectors. For one row, the selected raw-sector stream is:

```text
first = start_group_sector + XA_channel
last  = end_group_sector   + XA_channel
sectors = first, first + 8, ... last       # last is included
```

All selected nonterminal sectors have XA subheader file/channel/submode/coding
`1/<table channel>/0x64/0x01`. The included terminal sector is identical except
for EOF submode `0xE4`. These conditions, the duplicated XA subheader, Mode 2
header, BCD MSF address and all bounds are checked for every selected sector.
The stable standalone audio ID is the zero-based descriptor row, `0` through
`49`; no song, voice or character label is implied.

## Inventory

```powershell
python tools/xas_tool.py inventory `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --json workspace/xas/inventory.json `
  --csv workspace/xas/inventory.csv
```

If neither `--json` nor `--csv` is supplied, JSON is printed to standard
output. Existing requested files are preserved unless `--force` is supplied.
JSON and CSV ordering is deterministic and no current-time field is emitted.

The JSON contains two numeric namespaces:

- `xa_streams`: the 50 executable descriptor rows, with group and selected
  relative sectors, absolute LBAs, stride, sector count, subheader fields,
  exact raw byte size and SHA-256.
- `movie_regions`: 22 scan-derived regions, with first/last STR sector,
  contiguous raw span, frame count, dimensions, observed chunks per frame,
  STR/XA/padding sector counts and exact raw-span SHA-256.

Movie ID `0` through `21` is only the ascending scan order for this verified
revision. A boundary is proved when a structurally valid STR stream resets to
chunk 0 of frame 1. Within each region, every frame starts at 1 and increases
without gaps, every chunk is present in order, frame metadata agrees across
chunks, and dimensions remain constant. The raw span runs from the first
through last validated STR sector and includes its interleaved XA channel 1
and padding sectors. The three gaps between nonadjacent regions are not
silently assigned to either neighbor.

The complete validated XAS sector mix is:

| Submode | Meaning used by this tool | Count |
|---|---|---:|
| `0x00` | padding | 4,595 |
| `0x48` | real-time STR data | 111,099 |
| `0x64` | real-time XA audio | 133,807 |
| `0xE4` | terminal XA audio/EOF | 51 |

## Read-only extraction

Selections use comma-separated IDs and inclusive ranges. At least one
selection is required, preventing an accidental several-hundred-megabyte dump:

```powershell
python tools/xas_tool.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output workspace/xas/streams `
  --xa-ids 0,4-6 `
  --movie-ids 0,21
```

An XA output such as `xa-000.raw` concatenates only that descriptor's selected
2352-byte sectors in playback order, including its terminal EOF sector. A
movie output such as `movie-021.str.raw` contains every unaltered 2352-byte
sector in the cataloged contiguous span, preserving its STR/XA interleave.
`inventory.json` and `inventory.csv` are written beside the payloads. Writes
use a temporary file and atomic replace; `--force` is required to replace
matching files.

## Current boundary

This tool is a strict catalog and local extraction oracle, not an XA/STR
encoder. Its companion `xas_mod.py` accepts already encoded, author-owned
sector streams and builds guarded, exact-budget replacements; see
[`XAS_MOD.md`](XAS_MOD.md). The companion validates framing, subheaders,
EDC/ECC, channel/coding, interleave and STR structure. XAS is raw Mode 2 media,
so runtime replacement uses guarded `disc_raw` operations rather than the
`disc_user` coordinate system used for ordinary ISO/BNS bytes.

Run all synthetic tests with:

```powershell
python -m unittest discover -s tools/tests -v
```

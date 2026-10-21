# System 12 model research

`arcade_model_probe.py` verifies local arcade ZIP files against pinned MAME
ROM definitions, reconstructs their memory regions, extracts exact raw models
from canonical ARC directories, and compares them with PS1 or live arcade data.
It does not import a character into Tekken 3 or export an editable mesh.

The later playable renderer/stance experiment is documented separately in
[JUN_IMPORT.md](JUN_IMPORT.md), including the remaining combat and selector work.

## Verified first result: Jun

On 2026-09-12, the TTT1 `tektagt` set passed verification for all 15 ROM chips.
The reconstructed banked region contains 126 complete `3DMK` records in two
directory-bounded ARC containers:

| ARC region offset | Members | Model records |
|---|---:|---:|
| `0x014DA698` | 109 | 109 |
| `0x0320A760` | 23 | 17 |

Jun's blue-top character-select model is member **046** of the first ARC.
Its 44,732 bytes have SHA-256
`c436fbe39bbc98acf24e72a9919812253e95f948ce7a0cd500f9d3f50ef10ddc`.
The character identity was established with a simultaneous MAME game-screen
capture displaying JUN and a RAM capture. Every byte of this model matches
the loaded record at physical RAM offset `0x00354108` after reversing exactly
168 additive pointer relocations with delta `0x80354108`. No other extracted
model passes this complete comparison for that capture.

All 126 TTT1 records have 30 rows of 56 bytes, while all 52 model records in
the verified PS1 BNS have 27 rows. Shared structure alone does not prove
matching bone meanings, primitive formats, texture layouts or animation use.
The original `model_map.py` base-8 navigation intervals remain conservative
structural slices; the observed live relocation delta is recorded separately
and must not be confused with that navigation convention.

The simultaneous Jin capture strongly matches first-ARC member 088, but two
words additionally change (file offsets `0x390` and `0x470`, row 15/19 word 12).
The exact identification command correctly reports zero complete matches for
that capture. Those updates need tracing before the data is treated as a
simple transferable model. Their semantic purpose has not been proved.

## Commands

Run from the repository root. Choose fresh output paths; the tool refuses to
overwrite existing outputs. Downloaded ROMs, emulator files, reconstructed
regions, extracted models and RAM captures belong under ignored `workspace/`.
The checked-in manifest contains only ROM metadata, with a pinned source URL,
commit, file hash and attribution.

```powershell
python tools/arcade_model_probe.py prepare `
  --romset workspace/jun-import/roms/tektagt.zip --set tektagt `
  --output workspace/jun-import/ttt1

python tools/arcade_model_probe.py extract-models `
  --region workspace/jun-import/ttt1/bankedroms.bin `
  --output workspace/jun-import/ttt1-models

python tools/arcade_model_probe.py compare `
  --region workspace/jun-import/ttt1/bankedroms.bin `
  --ps1-exe disc/SLUS_004.02 `
  --ps1-source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output workspace/jun-import/ttt1-vs-ps1.json

python tools/arcade_model_probe.py identify-live `
  --ram workspace/jun-import/jun-select-ram.bin `
  --models workspace/jun-import/ttt1-models `
  --output workspace/jun-import/jun-identification.json
```

`prepare --regions maincpu:rom,bankedroms,c352` explicitly selects a subset of
regions. This was used for the Tekken 3 comparison because the downloaded
MAME 0.264 set has the older `tet1verb.11s` sound CPU image, while the pinned
current `tekken3` definition requests `tet1vere.11s`. The unsupported sound
CPU was excluded, not relabelled or accepted with a mismatched hash. All 12
chips in the requested Tekken 3 regions verified successfully.

The probe finds 32 `3DMK` signatures in the reconstructed Tekken 3 arcade
bank, of which only two match the PS1-observed envelope. The rejected hits
remain in the report; compressed data and other formats are not decoded by
this probe. Neither arcade bank contains an exact complete PS1 BNS model.
This is an exact-byte result, not evidence against format conversion.

## Validation and boundaries

ZIP members are read in memory, never extracted using archive-provided paths.
Size, CRC32 and SHA-1 must all match before a chip is used. ROM loading handles
the byte, 32-bit word-lane and swapped-word layouts present in the manifest,
with bounds and overlap checks. Unpopulated region bytes are zero-filled.

A signature scan alone intentionally reports `record_size = null` and
`semantic_name = null`. `extract-models` establishes record sizes from strict
ARC directories before calling the existing full model structural parser.
Numeric members remain unnamed until supported by independent game evidence.
`identify-live` validates a full model against RAM allowing only the observed
additive relocation. Other changes fail that exact comparison.

```powershell
python -m unittest tools.tests.test_arcade_model_probe tools.tests.test_model_map tools.tests.test_arc_tool -q
```

The 29 tests cover lane ordering, bounds, overlap, damaged ZIP contents,
signature false positives, archive boundaries, exact live relocation matching,
and the existing ARC/model parsers. Real-data verification and the live Jun
capture supplement those synthetic tests.

## Remaining work

1. Trace the model initialization and the additional Jin model updates.
2. Decode Jun's geometry/material/texture references and validate a visible
   editable export. The current `.3dm` is an exact original binary record.
3. Establish the relationship between the 30-row and 27-row layouts using
   actual animation/rendering behavior. Do not discard rows based on count alone.
4. Fit or relocate assets in the PS1-based runtime, then test Jun with Jin's
   full moveset, throws and hit reactions in an isolated replacement mod.
5. Add a distinct character identity and selection entry after the replacement
   prototype works.

The game executable, launcher, roster, existing mods and saves were not changed
by this first extraction milestone.

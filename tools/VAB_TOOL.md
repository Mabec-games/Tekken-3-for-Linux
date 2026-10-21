# Verified VH/VB reconstruction

`vab_tool.py` audits and reconstructs the split Sony PlayStation VAB sound
banks in **Tekken 3 (USA), SLUS-00402**. It uses only the Python standard
library and the project's read-only `bns_tool.py` source adapter.

The tool never changes the executable, `TEKKEN3.BNS`, or a BIN/CUE. A
reconstructed `.vab` contains retail audio data. Keep it under the gitignored
`workspace/` directory, and never commit, publish, or ship it.

## What was verified

There are 48 split banks in the supported archive. For each bank:

1. A top-level BNS record contains a Sony `pBAV` version-7 VH header.
2. The immediately following BNS record is a five-member ARC.
3. ARC member `2` is the raw VB payload.
4. `VH declared total size - exact VH record size` equals that member's size.
5. The VH's 256-entry VAG size table independently sums to the same VB size.
6. The member divides exactly into the declared samples, and every sample has
   valid SPU-ADPCM block headers, flags, alignment, and a final end flag.

All six conditions hold for every known pair. Extraction still requires both
numeric BNS IDs explicitly; the tool refuses arbitrary adjacency or a merely
similar-sized ARC member.

The verified pairs are:

```text
72/73   76/77   80/81   84/85   88/89   92/93
96/97   100/101 104/105 108/109 112/113 116/117
120/121 124/125 128/129 132/133 136/137 140/141
144/145 148/149 152/153 156/157 160/161 164/165
168/169 172/173 176/177 180/181 184/185 188/189
192/193 196/197 200/201 204/205 208/209 212/213
216/217 220/221 224/225 228/229 232/233 236/237
240/241 244/245 248/249 252/253 256/257 276/277
```

Each item is `VH_ID/ARC_ID`. IDs are the stable zero-based US BNS table
indices documented by `BNS_TOOL.md`.

## Audit all pairs

The audit performs the complete structural and audio-framing validation and
writes hashes and proof fields, but no payload files:

```powershell
python tools/vab_tool.py audit `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --json workspace/vab/audit.json
```

Omit `--json` to print the JSON manifest to standard output. The executable is
accepted only when its SHA-256 matches the supported SLUS-00402 file. The
Track 1 ISO location of `TEKKEN3/TEKKEN3.BNS;1` is discovered rather than
hard-coded. A standalone, locally extracted `TEKKEN3.BNS` is also accepted.

The audit manifest records:

- the executable, BNS table, and source/container identity;
- all 48 explicit VH/ARC IDs and the VB member index;
- BNS-relative sectors, offsets, exact sizes, and SHA-256 values;
- VAB version, bank/program/tone/VAG counts, and individual sample sizes;
- independent proof booleans for adjacency, unique member matching, declared
  size, size-table total, and SPU-ADPCM validation;
- the deterministic reconstructed size and SHA-256 without writing the VAB.

## Reconstruct one bank

Supply both sides of one verified pair:

```powershell
python tools/vab_tool.py extract `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --vh-id 72 `
  --arc-id 73 `
  --output workspace/vab/072.vab
```

The result is deterministic byte concatenation after validation:

```text
072.vab = exact bytes of BNS record 72 + exact bytes of ARC 73 member 2
```

The default manifest is `072.vab.json`; override it with `--manifest PATH`.
Both files use temporary-file/atomic-replace writes, and existing outputs are
preserved unless `--force` is supplied. Even with `--force`, resolved output
paths may not alias the executable or BNS/disc input.

For the verified stock pair `72/73`, the result is 73,936 bytes. Its VH
declared size equals the actual output size, and the output begins with
`pBAV`. These values are observations for validation, not retail payloads.

## Strict boundary

This tool reconstructs a conventional analysis copy; it does not decode VAGs
to WAV, edit tones, replace audio in the game, rebuild an ARC/BNS, patch the
executable, or produce redistributable assets. It also does not guess unknown
pairs. Any future replacement path must preserve the game loader's ARC member
layout and separately validate runtime size/relocation constraints.

Run all local tool tests with:

```powershell
python -m unittest discover -s tools/tests -v
```

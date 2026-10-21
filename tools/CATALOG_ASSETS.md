# One-command local asset catalog

`catalog_assets.py` verifies the exact Tekken 3 USA executable and raw Track 1,
then runs the checked-in read-only analyzers as one operation. It writes a
single deterministic JSON metadata catalog. It never extracts or embeds retail
asset payloads.

```powershell
python tools/catalog_assets.py `
  --exe disc/SLUS_004.02 `
  --source "disc/Tekken 3 (USA) (Track 1).bin" `
  --output workspace/catalog/assets.json
```

The executable must match `SLUS-00402`; the source must match the exact
632,532,768-byte raw Mode 2 Track 1 documented by the individual tools. A
standalone BNS or cooked ISO is deliberately rejected because it cannot prove
the raw XAS media.

The command produces metadata for:

- all 303 top-level BNS records and their conservative kinds/hashes;
- all 48 verified split VH/ARC/VB sound-bank relationships;
- all 50 executable-defined strided XA streams;
- all 22 scan-derived STR movie regions;
- the optional `model_map.py` model-section scan when its stable public API is
  installed; absence is explicitly reported and is not treated as corrupted
  BNS/XAS metadata.

The wrapper hashes the full Track 1 once, discovers the BNS ISO extent once,
and shares the verified executable/BNS table with the BNS and VAB analyzers.
The XAS analyzer still validates every raw sector and hashes the exact XAS span
as its independent structural proof.

The output declares `metadata_only: true` and
`retail_payloads_extracted: false`. Its final `catalog_sha256` hashes the
canonical JSON value before that field is added. Local executable, Track 1 and
output paths are not emitted or hashed: moving the same verified inputs to a
different directory, or spelling their paths differently, produces the same
catalog and `catalog_sha256`. Stable logical roles, sizes and content hashes
identify the inputs instead. No timestamps or host-specific random values
enter the document, and record/media arrays remain in stable numeric order.

The unified model summary retains numeric IDs, structural ranges, metrics and
SHA-256 values. Literal byte samples (`prefix_hex`), raw row words, entropy
sample blocks and offset-reference drill-downs stay only in the dedicated,
gitignored `model_map.py` research inventory. They are deliberately stripped
from this payload-free aggregate catalog.

Existing output is preserved unless `--force` is supplied. Even with
`--force`, the output may not resolve to the executable or Track 1 input. File
creation uses a same-directory temporary file followed by an atomic replace.
Use `--no-models` when only the mandatory analyzers are wanted.

The catalog itself contains hashes, sizes, offsets and structural metadata,
not the corresponding game bytes. Any later extraction performed through an
individual tool still contains retail data and must remain under ignored local
directories.

Run its focused tests with:

```powershell
python -m unittest tools.tests.test_catalog_assets -v
```

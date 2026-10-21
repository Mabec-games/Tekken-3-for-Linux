# Guarded XAS media package builder

`xas_mod.py` turns already encoded, author-owned Tekken 3 XA audio streams or
STR movie spans into default-off PSXRecomp `.psxmod` features. It never writes
the BIN/CUE or creates a patched disc.

This is an encoded-sector adapter, not a media encoder. Create and encode your
source audio/video with a suitable PlayStation XA/STR tool, then pass the
complete 2352-byte Mode 2 sectors to this builder.

## Exact revision

Only the verified US release (`SLUS-00402`) is accepted:

| Property | Required value |
|---|---:|
| Raw Track 1 size | `632532768` bytes |
| Raw Track 1 SHA-256 | `6b660e62748d02779e9e08362a5ed202540af7fad134de2ec0a2184ad78bb496` |
| Executable SHA-256 | `fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c` |
| XAS ISO extent | LBA `604`, `249552` raw sectors |

Run `xas_tool.py inventory` first to inspect the 50 executable-backed XA IDs
and 22 scan-derived movie IDs, including sector budgets and dimensions.

## XA package

An XA input must contain exactly the selected descriptor's stock sector count.
Every sector requires valid sync, BCD address bytes, Mode 2, duplicate
subheaders, Form 2 EDC, file 1, the descriptor channel, coding `0x01`, and
submode `0x64`; its last sector alone must be terminal `0xE4`.

```powershell
python tools/xas_mod.py `
  --package-id example.xa-pack `
  --version 1.0.0 `
  --name "My XA Pack" `
  --author "Mod Author" `
  --license CC-BY-4.0 `
  --xa-replacement "004=mods/workspace/my-xa/xa-004.raw" `
  --output out/my-xa-pack-1.0.0 `
  --archive out/my-xa-pack-1.0.0.psxmod
```

The format-6 overlay maps one 2336-byte authored sector body every eight raw
disc sectors. The seven sibling channels are gaps, not package payload,
collision claims, or writes.

## STR movie package

A movie input must fit its discovered contiguous raw-sector span exactly. The
accepted stock envelope is:

- STR sectors `1/1/0x48/0x00`, with structurally valid chunks and one frame
  sequence beginning at frame 1;
- movie XA sectors `1/1/0x64/0x01`;
- padding sectors `1/0/0x00/0x00`.

Form 1 STR/padding sectors require valid EDC plus ECC P/Q; Form 2 XA requires
valid EDC. Terminal `0xE4` is rejected because verified movie spans do not own
the shared XAS terminator. Width and height must match stock. Frame count may
change only when the authored stream remains one valid sequence inside the
exact sector budget.

```powershell
python tools/xas_mod.py `
  --package-id example.movie-pack `
  --version 1.0.0 `
  --name "My Movie Pack" `
  --author "Mod Author" `
  --movie-replacement "000=mods/workspace/my-movie/movie-000.str.raw" `
  --output out/my-movie-pack-1.0.0 `
  --archive out/my-movie-pack-1.0.0.psxmod
```

Movie inputs author every sector in the span, including interleaved channel-1
audio and padding. A selected XA stream that intersects a selected movie is
rejected; put overlapping alternatives in separate packages.

## Guard and publishing boundary

Only bytes 16..2351 of each input sector enter the package; absolute
sync/MSF/mode bytes remain stock. Every default-off feature pins the exact
game, executable, disc hash, first LBA, `chunk_size = 2336`, stride, count,
payload hash, and stock hash over the same logical chunks. The runtime indexes
and collision-checks only owned LBAs.

The tool validates structure, not authorship. Never publish retail extracts,
byte-identical validation packages, or media you lack permission to
redistribute. Keep retail-sector oracles under ignored `workspace/` or a
temporary directory.

```powershell
python -m unittest tools.tests.test_xas_mod -v
.\scripts\dev.ps1 test
```

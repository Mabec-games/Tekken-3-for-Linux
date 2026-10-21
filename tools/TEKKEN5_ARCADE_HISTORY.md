# Tekken 5 PS2 Arcade History research notes

These notes describe the USA retail image currently present in the repository
root.  They document local analysis only; no disc image or extracted retail
payload should be committed or redistributed.

## Input identity and Git boundary

- Disc: `Tekken 5 (USA).iso`, 4,483,547,136 bytes
- SHA-1: `aec7958a90d603daec0bf850f2f0eb19029cf11f`
- MD5: `7472a628307a0e4309aef66c14d6dbc4`
- The root `.gitignore` already ignores `*.iso`.
- All generated retail-data output is under `/workspace/`, which is also
  ignored.

## Disc layout and extractor

`TK5DATA3.BIN` is the Arcade History package.  `TK5DATA5.BIN` is an exact
duplicate (SHA-1 `f91897edd6564cff3497a0602db4ecf4743c1b51`).  The package has a
10-entry, sector-aligned outer directory.  Entry 7 contains a 72-file named
directory covering Tekken 1, Tekken 2, and Tekken 3 assets.

Run the extractor against a mounted legal dump:

```powershell
python tools/tekken5_arcade_history.py D:\TK5DATA3.BIN `
  workspace/tekken5-arcade-history
```

The recovered Tekken 3 group begins at named entry 48:

| Entry | Name | Size |
|---:|---|---:|
| 48 | `romdata.arc` | 14,763,208 |
| 49 | `MOT_FHEAD.bin` | 4,399,360 |
| 50 | `t3movie.pss` | 3,325,956 |
| 51-70 | 20 `TK5STRM0` `.ovb` audio containers | 70,224-8,143,024 |
| 71 | `irx.pak` | 95,488 |

The outer entries 0-2 use a small flag-byte/LZ codec.  The recovered Tekken 3
executable is a native PS2 ELF, 8,820,472 bytes, SHA-256
`6802704e1da98fb345293ece07b3675492ec96fbad246eb08ff1ab67397aa41a`.
Its `.text` section starts at EE virtual address `0x0016f600`; the huge
`.rodata` section includes converted game data and the original operator-test
content.

## Confirmed dormant game-mode code

This is more than a string-table artifact.  The executable contains code that
selects and renders the home-style modes which Arcade History does not expose
through its normal front end.

- The central mode word is read at EE address `0x00208128`.
- Function `0x001acd58` dispatches that word through the jump table at
  `0x003e35b8`.
- Mode 2 reaches `0x001acea0` and renders the misspelled built-in label
  `TEMA BATTLE` at `0x003e3570`.
- Mode 4 reaches `0x001acec8` and renders `SURVIVAL BATTLE` at `0x003e3588`.
- Mode 5 reaches `0x001acee0` and renders `PRACTICE MODE` at `0x003e35a0`.
- The HUD renderer at `0x00196d00` has explicit cases for Team Battle, Time
  Attack, and Survival.  Its table is at `0x003e1f68`.
- A separate seven-way result renderer at `0x001a10f0` has live branches for
  `TIME ATTACK!`, `SURVIVAL!`, and `PRACTICE!`.

The static evidence therefore confirms compiled mode logic and presentation,
not merely unused English text.  A runtime patch has **not** yet been verified.
Forcing only `0x00208128` may skip required initialization, so it should be
treated as a tracing lead rather than a finished cheat.

## Confirmed dormant Jun and Sake character records

The port retains real character descriptors for **Jun** and **Sake**, not just
incidental text.  Run the correlation probe with the ignored local System 12
source used by the Jun importer:

```powershell
python tools/tekken5_t3_character_probe.py `
  --arcade-bank workspace/github-release/easy-release/app/workspace/jun-import/t3-arcade/bankedroms.bin `
  --ui-report workspace/github-release/easy-release/app/workspace/jun-import/jun/ui-report.json
```

- Jun's descriptor is at ELF file offset `0x2e3160` / EE address
  `0x003e2160`; Sake's follows at `0x2e3170` / `0x003e2170`.
- The live 23-character-by-four-costume lookup at file offset `0x108fb8`
  maps all four entries for character ID 17 to Jun and all four entries for
  character ID 21 to Sake.  This rules out the earlier hypothesis that the
  names were merely default ranking initials.
- Both records contain movement-bank selector 9, the value used by Jin's
  normal descriptor.  This agrees with public arcade experiments in which
  the incomplete characters borrow Jin's moves.
- Three original System 12 Jun graphics survive byte-for-byte as their
  original compressed streams in `romdata.arc`, each as member 17 of its
  asset group: the 168x252 versus portrait, a 44x68 selector portrait, and a
  44x58 selector portrait.  Their decompressed SHA-256 hashes are respectively
  `ae1f58b29c30d6b8ed6baaac7c5c13ce9ad9b3d74d42207f55f88b73ee9081db`,
  `c55e8ab6928b9b549f26a172f71dace0758943b9bddd8f4b60f6f9d68173548b`,
  and `0914af495dd9c68a85df984ba16f7ad1e2a0ce7fc9c0929d90151a8912e66753`.

This establishes a dormant Jun slot plus authentic presentation art in the
Tekken 5 port.  It does **not** establish a complete Jun model or original Jun
moveset: the descriptor deliberately selects Jin's movement bank, and arcade
experiments report a borrowed Nina body.  Sake's descriptor is equally real,
but no unique Sake portrait or finished fish model has been established.

Kazuya is weaker evidence.  `KAZUYA` does not occur in the Tekken 3 ELF, there
is no Kazuya descriptor in the 23-entry lookup, and no `kazuya.vb/.vh` filename
exists in its sound-bank table.  Community databases report an unused Kazuya
announcer call and a hacked, unnamed moveset sometimes attributed to him, but
neither has yet been mapped to a specific PS2 asset, so this report does not
label either one confirmed.

## Deeper art, roster, and stage census

Run the visual/data census against the ignored extraction and the verified
System 12 bank:

```powershell
python tools/tekken5_t3_deep_probe.py `
  --arcade-bank workspace/github-release/easy-release/app/workspace/jun-import/t3-arcade/bankedroms.bin
```

The generated report and contact sheets are written under the ignored
`workspace/tekken5-t3-deep-probe/` directory.  The most important discovery is
the 25-member character-name graphic archive (`romdata.arc` entry 5).  It
contains finished 16-pixel-high name strips for the normal roster plus:

| Member | Graphic | Original System 12 decoded-stream offset |
|---:|---|---:|
| 17 | `JUN` | `0x10e95e8` |
| 19 | `SOUL` | `0x10e984c` |
| 20 | `INSECT` | `0x10e9978` |
| 21 | `SAKE` | `0x10e9ad0` |
| 22/24 | duplicate `PANDA` | `0x10e9c40` |
| 23 | `TIGER` | not found by the bounded decoded-stream comparison |

The Jun, Soul, Insect, Sake, and Panda graphics decode identically to streams
in the original arcade bank.  This proves they are authentic Tekken 3 assets,
not stray Tekken 5 text.  Public documentation identifies **Soul Jackson** as
Tiger Jackson's pre-production name, so `SOUL` is best classified as an early
Tiger label rather than a separate fifth cut fighter.  `INSECT` is much more
interesting: it is finished local name art for the documented cut giant
praying-mantis concept, although this port has no Insect descriptor or model
identified so far.

The portrait archives establish at least four separate Jun presentation
assets in this PS2 port: the `JUN` name strip, two selector portraits, and a
168x252 versus portrait.  Sake has a descriptor and authentic name strip but
still no unique portrait or fish model.  One 168x252 portrait member is a plain
white `WHO IS IT?` silhouette.  Other retained UI includes a `NEW` badge,
`CHARACTER TIME RECORD`, `VS GAME WINS RECORD`, and `CHARACTERS`, matching the
arcade cabinet's timed character-release presentation.

The character-model archive contains exactly 41 bundles, and every bundle has
one valid decoded `3DMK` model part plus textures.  A rendered texture census
looks like the released roster and costume variants; it did not reveal a
unique Jun, Sake/fish, Insect/mantis, Soul, or Kazuya model.  This is a strong
negative census, not a proof that no unreachable geometry can exist elsewhere
in the package.

The 25 descriptor variants examined use stage IDs `0` through `12` only.  Jun
and Sake both select stage ID 10, the same stage used by Eddy and Tiger, and
both use the generic hidden-character music/sound value 17.  They therefore do
not have descriptor-assigned unique stages or music in this build.  No local
asset has yet been tied to the possible coliseum-like prototype stage visible
in pre-release magazine screenshots, so that remains external prototype
evidence rather than a recovered stage from the Tekken 5 disc.

Context for interpreting these assets:

- MAME's primary source shows that the Tekken 3 revisions use the same banked
  ROM set and documents its layout:
  <https://raw.githubusercontent.com/mamedev/mame/master/src/mame/namco/namcos12.cpp>
- Tiger's pre-production `Soul Jackson` name and unused announcer call are
  documented here: <https://tekken.fandom.com/wiki/Tiger_Jackson>
- The planned giant praying-mantis `INSECT` character is summarized here:
  <https://www.vgfacts.com/game/tekken3/>
- The arcade time-release system's `WHO IS IT?`/`COMING SOON` presentation is
  described in this contemporary FAQ:
  <https://gamefaqs.gamespot.com/ps/198900-tekken-3/faqs/1074>
- The prototype-stage screenshots are collected here, but are not local proof:
  <https://www.resetera.com/threads/tekken-3-magazine-coverage-from-edge-next-generation-egm-gamefan-and-more.1456336/>

Public comparisons:

- <https://www.youtube.com/watch?v=X8AqtZ7G5Cc> demonstrates the arcade Jun
  and Sake slots.
- <https://adb.arcadeitalia.net/dettaglio_mame.php?game_name=tekken3a&search_id=>
  records the known Jun/Sake behavior and reports unused announcer calls for
  Jun, Kazuya, and Sake.
- <https://tekken.fandom.com/wiki/Sake> preserves Katsuhiro Harada's account
  of the abandoned salmon concept and describes the incomplete arcade slot.

## Arcade operator test suite

The port retains the full System 12 operator suite: display/color/convergence,
switch, sound, game options, data clear, and ranking clear.  It also retains
settings such as `CHARACTER CHANGE AT CONTINUE`, `CHARACTER CHANGE AT VS GAME`,
`EVENT MODE`, and the internal identifier `TEKKEN3A`.

This suite is obscure but not truly inaccessible in Tekken 5: Select is mapped
to the arcade test input.  Use Select by itself after entering the embedded
game.  Start+Select is also used by the Arcade History wrapper to return, so
avoid pressing the pair accidentally.

The original operator manual describes the same screens and options:

- <https://arcarc.xmission.com/archive/PDF_Arcade_Manuals_and_Schematics/Tekken_3_Operations_Manual.pdf>

## Embedded PlayStation sound banks and the Gon lead

The PS2 ELF contains 23 structurally valid Sony VAB sound banks.  Their on-disc
layout is unusual: each bank is stored as `VB sample data + VH header`.  The
carver reverses them into conventional `VH + VB` files and validates every
SPU-ADPCM sample boundary and end marker:

```powershell
python tools/tekken3_ps2_vab.py `
  workspace/tekken5-arcade-history/executables/tekken3.elf `
  workspace/tekken5-vab-carve-verified `
  --ps1-audit workspace/vab/real-audit.json
```

Result: all 23 banks validate, and 21 are byte-for-byte identical to banks in
the repository's verified Tekken 3 USA PS1 audit.  Two are port-specific or
modified.

The executable also retains `.vb`/`.vh` filename tables for 21 banks, including
`gon.vb` and `gon.vh`, even though Gon is a PlayStation home-version guest and
is not part of the Tekken 3 arcade roster.  This is a strong unused-content
lead, but the filename table has not yet been tied to the 23 embedded-bank
order by a proven pointer table.  What is confirmed today is:

1. the Gon filenames are present;
2. actual validated PS1 sound banks are embedded;
3. the character model, moves, selection data, and reachability of Gon are not
   established by those audio facts.

## `test.ovb`

Named entry 46 is a literal `test.ovb`, but it belongs to the Tekken 2 group,
not Tekken 3.  It is a valid `TK5STRM0` container:

- SHA-256: `06429de331cd5b11cec04d2be85af6d73fafcbb25e694456430aecff764633b1`
- PlayStation ADPCM, 44.1 kHz, stereo
- 540,008 samples / 12.245 seconds
- The channels are strongly independent and contain broad-band tonal/music
  content rather than silence or a simple fixed sine tone.

The decoded analysis copy is
`workspace/tekken5-arcade-history/tekken2/test.wav`.  Its exact purpose and
whether retail code calls it still need an executable reference trace.

## Web cross-checks

- Sony describes Tekken 5 as containing playable ports of arcade Tekken 1-3:
  <https://blog.playstation.com/?p=402360>
- MAME's primary System 12 source documents the Tekken 3 revisions and ROM
  layout:
  <https://github.com/mamedev/mame/blob/master/src/mame/namco/namcos12.cpp>
- vgmstream lists `.ovb` specifically for Namco Collection and Tekken 5's
  Tekken 1-3 ports:
  <https://github.com/vgmstream/vgmstream/blob/master/src/formats.c>
- Existing reverse-engineering notes describe the sector-aligned `TK5DATA*`
  bigfiles and their obfuscated retail resources:
  <https://reshax.com/topic/1855-ps2-tekken-5-bin-files-looking-for-file-tables/>

## Next useful probes

1. Trace every write to `0x00208128`, then reproduce the required init sequence
   for modes 2-5 in PCSX2.
2. Identify the two port-specific VABs and map the 21 filename entries to bank
   indices; this will confirm whether a complete unused Gon bank survives and
   provide the best route to testing the reported Jun/Kazuya/Sake announcer
   calls.
3. Trace `test.ovb` from the Tekken 2 ELF and compare it with the operator sound
   test selections.
4. Trace Jun/Sake descriptor field use and the portrait loaders in PCSX2, then
   determine whether the wrapper blocks IDs 17/21 or only the selector does.
5. Map the 41 character-model bundles to final character/costume names using
   runtime loader references, then compare their `3DMK` skeleton and mesh
   structures for geometry that the texture contact sheet cannot identify.
6. Trace every reference to name members 19-21 and the `WHO IS IT?` silhouette
   to determine whether the Soul/Insect/Sake and timed-release resources still
   have reachable code paths.

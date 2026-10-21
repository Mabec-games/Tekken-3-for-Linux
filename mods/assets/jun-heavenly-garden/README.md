# Jun — Heavenly Garden, native stage 20

Status: **integrated and packaged in the release build; gameplay validation pending**.
Jun owns a separate stage, ID 20, retaining Jin's music (16). Original stages
0–19 and disc data are unchanged. Tekken Force/Ball retain their mode-owned
arenas. The new arena follows native home/opponent ownership, not every fight
where Jun is present. Select Jun as the opponent in VS/Practice to test it.

## Deliverables

- `background.png`: 2172 x 331 full-colour panoramic backdrop, redrawn without
  baked-in pixel blocks; horizontal wrap boundaries match.
- `ground.png`: 64 x 64 almost-flat, still lavender-grey water, 16 colours, RGB555-precision
  palette; both horizontal and vertical wrap boundaries match.
- `background.rgba`, `ground.rgba`: the same authored pixels in the
  existing host `HDRGBA01` payload format. These alone do not install a stage.
- `background-wrap-preview.png`: enlarged right-to-left join for inspection.
- `ground-repeat-preview.png`: 3 x 3 repeated floor with nearest-neighbour scaling.
- `source/`: unmodified built-in image-generation outputs.
- `clarity-colour-prompts.json`: built-in image-generation prompt for the active
  `background-clear-v2.png` source and the superseded v2 floor.
- `ground-water-v3-prompt.json`: exact built-in image-generation prompt for the
  active `source/ground-water-v3.png`, regenerated as softer, almost-solid water.
- `prompts.json` and earlier floor prompts: historical variants, not active.
- `art-report.json`: measured resolution, palette counts and edge checks.
- `native/Heavenly-Garden.arc`: native 8bpp background / 4bpp floor TIMs,
  environment metadata and padding within the stock stage buffer budget.
- `native/Heavenly-Garden.mesh`: stock cylinder topology with 640 remapped
  background primitives and neutral colour modulation.
- `native/manifest.json`: stage IDs, formats, sizes and SHA256s.
- `native/background.rgba`, `native/ground.rgba`, `native/background-mapping.bin`:
  full-detail host backdrop, decoded native water material, and ten guarded
  mappings (six backdrop pages plus four floor tiles) for OpenGL.
- `native-background-preview.png`, `native-floor-preview.png`: diagnostic
  reconstructions of the actual native texture data, not gameplay screenshots.

The art recreates Heavenly Garden's lavender sky, pale rainbows, floating
cherry-blossom island, lilies and water in a lower-fidelity rendering. This is
new generated artwork based on stage references, not a rip of TTT2 textures.
Large lilies remain in the backdrop; the floor is nearly uniform still water
with subtle tonal variation, no visible bed, stones, flowing ripples or flowers.

## Research and format

Visual references inspected on 2026-09-20:

- [Original TTT2 stage artwork gallery](https://tekkenwarehouse.com/tekkentag2/stages/)
  and its [Heavenly Garden image](https://tekkenwarehouse.com/wp-content/uploads/2025/01/ttt2_stage_unknown_heavenlygarden.png).
- [Heavenly Garden identification and scene description](https://tekken.fandom.com/wiki/Heavenly_Garden).
- [Heavenly Garden screenshot](https://static.wikia.nocookie.net/tekkenpedia-ita/images/3/3e/Heavenly_GardenTT2.png/revision/latest?cb=20200324171648&path-prefix=it).
- [Actual T3 Badlands texture sheet](https://textures.spriters-resource.com/playstation/tekken3/asset/383595/).
- [PS1 TIM/CLUT format reference](https://psx-spx.consoledev.net/cdromfileformats/#cdrom-file-video-texture-image-timpxlclt-sony).

The more specific T3 format findings below come from this project's extracted
disc records and working stage decoder, not assumptions from modern Tekken:

- `tools/forest_hd_pack.py` reads forest texture record 038 and backdrop model
  record 058. Background triangles/quads reference many individual 4-bit TIM
  tiles with shared CLUTs; the final VRAM palette upload is authoritative.
- Backdrop UVs are reconstructed from mesh vertex azimuth into a wraparound
  panorama. It is not a single fullscreen image pasted behind the fighters.
- The local reconstructed stock forest reference is 2048 x 512; its four
  floor patches are separate 64 x 64 textures, submitted independently.
- A convenient panorama PNG is an authoring asset, not a native T3 stage file.
  This pack converts it into six overlapping 160 x 192 native **8-bit** TIM
  pages, sharing one 256-colour RGB555 palette. The panorama is sampled at
  768 x 192. Each primitive uses its own angular position, avoiding the
  stock UV layout's repeated half-cylinder. The floor stays native 4-bit.
- Every upload is checked against the original stage's VRAM allocation;
  character models, fonts, effects and other UI texture regions are untouched.

The authoring panorama is approximately 6.56:1. Its horizontal coordinate
maps around the cylinder and its vertical coordinate to the backdrop height,
not to the screen aspect ratio. Native sampling is lower-resolution than the
authoring PNG and stock reconstruction. OpenGL uses the full 2172 x 331 authored
backdrop with linear/mipmap filtering and continuous colours. The simpler
prerendered shapes retain the older game-art style without fake pixel blocks;
only the native fallback is reduced to a PS1 palette. Ten HDMAP002
records check actual native pixel and palette identities before replacement;
backdrop and floor have distinct material kinds. Unrelated stages, the roof,
fighters and UI are excluded. Other renderers
retain the native 768 x 192 backdrop.
The generator's black padding and antialiased letterbox fringes are omitted.
Narrow texture gutters match wrap edges. Native palette reduction and RGB555
precision are deterministic build steps. The actual native floor's average
colour differs from the backdrop water at the join by less than 12/255 per
channel. The floor remains static and nearly uniform, without ripples or stones.
In OpenGL, matched opaque water no longer inherits the forest floor's dark
distance tint. The final 10% of the backdrop height fades smoothly into the
water texture's 1x1 average mip, reaching full agreement before the cylinder
edge. This is a material-UV transition, independent of screen aspect/camera;
it does not modify alpha, collision, fighters or shadow draw passes. The same
64x64 water material uses filtering/mipmaps to reduce distant tile speckling.

## Rebuild / checks

From the repository root, with Pillow and NumPy installed:

```powershell
python tools/jun_stage_art_pack.py
python tools/build_jun_stage.py
python tools/test_jun_stage.py
python tools/test_jun_background.py
python tools/test_jun_water_shader.py
```

The native builder requires the locally extracted, SHA-verified forest records
`workspace/forest-research/records/038.arc` and `058.bin`. It does not edit them.
If regenerated native files change, update their pinned hashes in
`src/tekken3_jun_stage.c` before building. CMake packages `native/` beside the
executable as `mods/jun-heavenly-garden/`.

Checks cover authoring wrap edges, colour budgets, native VRAM allocation,
buffer budgets and full panorama coverage. Offline execution of the real
native TIM uploader verifies all 22 upload rectangles/payloads. The production
stage initializer and loader are exercised against the local disc executable,
including stage 0–19 preservation, stage 20 lookups, missing/corrupt-pack
fallback, home-stage routes, mode isolation and stage-cache transitions.
The Arcade regression suite executes the native route assignment before the
stage chooser, covering 400 combinations of CPU side, costume, ladder index
and prior stage. It also checks stale home metadata and human-Jun matches
against stock opponents. The harness maps real Expansion 1 data addresses.
Clean host loading-entry wrappers apply ownership after the native chooser;
there is no guest trampoline or interpreter-only commit callback. The recorded
Survival fallback (Paul vs Jun, Eddy stage 10/music 1) is now a regression case.
Another 1,458 cases cover mode/side ownership, untouched non-Jun state, pending
versus loaded cache identity, and continuation-entry exclusion.
Both native previews were visually inspected. No game or save state was started.
The host matcher check covers 1280 background triangles and four distinct water
tiles, excludes 72 roof/adjacent-pixel/wrong-palette queries, and rejects changed
pixels or palettes after cache invalidation.
It also checks that the host image retains more than 256 colours and compares
the final TIM floor colours against the backdrop's water, not just source art.
The production GLSL is compiled, linked and drawn in an invisible standalone
WGL test window: the floor and backdrop endpoint agree across different vertex
shades, while normal and character-texture shading remains intact. This does
not launch the game. Gameplay/camera presentation checks remain with the player.

## Runtime design / remaining player checks

The native stage-table pointers are redirected to expanded private tables;
stage 20 loads the host pack only at the known stage texture/mesh call sites.
Before loading-screen entry, a scoped ownership check gives CPU Jun stage 20
and music 16 in normal match modes. It checks the native CPU-side field (not
a hardcoded P2); two-player VS/Team/Practice use the native arena-owner side.
Stage/music globals and cached mode bytes are updated together. An arena-loader
entry check also synchronizes the pending stage cache, retaining the loaded
identity so the native reload/reuse comparison remains correct. Resumed CPS
continuations, non-Jun owners and mode-owned Ball/Force arenas are untouched.
The stage works through native textured primitives without depending on the
OpenGL enhancement. Missing or mismatched native assets retain stage 8;
missing host backdrop assets leave the native Jun backdrop in place.

This is an adapted cylinder and static water material, not new TTT2 geometry,
animated ripples, reflections or splashes. Player checks still needed: camera
rotation, horizon and floor scale, loading transitions, Jun/Jin stage separation,
4:3/16:9 framing, and renderer presentation.

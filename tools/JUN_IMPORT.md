# Jun: independent roster experiment

Jun now occupies a new character entry in the PS1 recompilation. The experimental build has 22 selectable fighters: the 21 stock fighters plus Jun. Her character ID is 23 and her three outfit model IDs are 52, 53 and 54. ID 21 remains the Force enemies and ID 22 remains the empty-selection sentinel.

## Play

The local release and debug builds now include Jun. Run `Play-Tekken3-Recompiled.cmd` for the normal game; no preview launcher or environment variables are required. Jun's private assets and mod manifest are staged beside the executable during the build.

The September 13 recovery update fixes the reproduced upside-down throw victim, Jun's inverted shared hit reactions, and the backward-facing movement loop. The pose bridge converts between the receiving fighter's skeleton bases, including the previous pose used for blending. The converter now preserves terminal transitions and their half-turn flags: source alias C1's terminal `800B` becomes native `8B`, instead of a generic type 6 recovery. Eight terminal partner-swap flags are excluded in solo play while retaining their base transitions. Camera-facing transitions read the player index from actor `+12`, not its pitch at `+C`.

The subsequent joint-orientation fix replaces the earlier uniform half-turn with bases for individual joints. Shared poses show half-turns about X at the root and shoulders, a quarter-turn about X at the wrists, and half-turns about Z at the ankles. The remaining joints, including the head and limb hinges, share their axes. Conversion uses the parent and child bases in opposite directions for arcade poses on stock victims and native reactions on Jun. The previous pose used by the transition blender receives the same conversion. Native head tracking already uses the correct shared head axes.

Joint-orientation evidence is in `workspace/jun-import/joint-validation.json`; `recovery-validation.json` and `solo-validation.json` record earlier builds. The earlier position-only checks could pass with an upside-down head mesh. The new `joints` and `head` cases check actual head/foot matrix directions during the first twelve recovery frames after real hits in both directions (5 HP from Jun, 7 HP from Jin). A private C fixture compares all 18 joints against eight unblended native/shared arcade poses, in both conversion directions, and checks exact round trips. Native IK/compression differences are retained; this is an orientation regression, not identical-pose parity. Screenshots include `recovery-joints-hit.png`, `recovery-joints-idle.png` and `recovery-head-hit.png`. These are bounded regressions, not proof of every animation/opponent combination.

The selector spacing follow-up keeps both roster grids compact and centered in widescreen. Cabinet portraits have 3px gaps, matching the stock 35px cell pitch; the eleven-column 4:3 grid retains its tighter 33px pitch to fit. Team Battle keeps its 36px pitch and 4px gaps. Portraits, cursor halves, player labels, borders and Team Battle edge gradients remain aligned as one grid. Before/after screenshots and build-specific checks are recorded in `workspace/jun-import/selector-spacing-validation.json`.

Run the focused checks with `python tools/test_jun_recovery.py --case CASE`, using `joints`, `throw`, `mirror`, `head`, `back` or `back-p2`. The second-slot turn uses the native transition queue because the debug input injector controls only the first pad. Automated fixtures use SDL's silent audio device; manual previews can use `--muted` without changing the normal game's audio settings.

For an isolated selector fixture, run `Play-Tekken3-Jun-Selector.cmd`, or:

```powershell
python tools/launch_jun_preview.py --selector --roster
```

Jun is the top-right tile in the cabinet selector and the last tile in Team Battle. Select her with a normal attack button. Jin retains his own tile. Arrows move, Z/A punch, X/S kick, and Enter pauses. `Play-Tekken3-Jun-Team.cmd` opens Team Battle directly. The launcher creates a dated executable/settings/save/asset copy and leaves other running games alone. Assets are copied with the executable so an export during development cannot change the format an already-open preview loads after selection. The old `Play-Tekken3-Jun-Preview.cmd` remains a direct-fight reference.

## Implemented

### CPU opponent integration (September 20)

`tekken3_jun_cpu.h` applies signature-guarded patches to BNS record 5's
Arcade/Time Attack, Team Battle, and Survival generators. It adds bit 23 without
enabling IDs 21 (Force enemies) or 22 (empty). Arcade's first four stock-roster
matches and final Heihachi/Jin + Ogre progression are retained; Jun is eligible
in its remaining random matches. Survival includes Jun in every progression
tier. BNS record 0's new-run reset loops cover all 24 counter indices; the mode
union accommodates Team counters through +A3 and Survival counters through +8F.
The same-address Force overlay is deliberately untouched.

The 12-byte per-character CPU parameters at 80098260 are extended privately;
Jun uses Jin's spacing/response parameters, while the native 3-by-10 difficulty
and progression profile matrix is unchanged. This table is read for both the
CPU and its opponent. Character-specific callback dispatch defaults safely for
Jun; Jin's special-case callbacks are not assigned to her.

Native CPU initialization caches move aliases in 8009F2E8[index] and CPU state
+0C. The 80059890 entry wrapper refreshes both from the installed Jun actor
before decisions, so initialization/round/team timing cannot leave Jin's
shorter donor table behind. CPU candidates then resolve through Jun's imported
aliases. The 8002CD7C wrapper supports the converter's E000+ command patterns
only for an installed Jun CPU actor. The current pack contains 147 native-format
command IDs and zero E000+ patterns; native commands remain native.

Jun's descriptor explicitly copies Jin's stage/BGM bytes (8/16). Ball/Force
mode-specific arena overrides remain native.

Run `python tools/test_jun_cpu.py` for offline production-C wrapper/patch tests
and Unicorn execution of original disc routines (requires `pip install unicorn`).
Coverage includes randomized routes, stock bosses/exclusions, Team sizes and
preselected Jun, Survival anti-repeat/tallies, dirty new-run resets, Force-overlay
isolation, all 30 native difficulty/progression settings with three Jun/opponent
orientations, every actual command ID, and three synthetic extended sequences.
These checks do not establish live combo quality or full gameplay parity. No
game process or save state is started by this test.

| Component | Current result |
|---|---|
| Roster | Separate character 23/models 52–54; 22-cell cabinet grid (11 columns) and Team Battle grid (8 columns); native confirmation and widescreen cursor/portrait alignment |
| Geometry | Three original TTT1 meshes (44,732 / 44,436 / 47,740 bytes); 168 / 164 / 172 verified relocations; 30 donor rows adapted to 27 native rows |
| Textures | All 26 / 22 / 28 source TIM tiles and palettes; separate player texture pages and packet buffers |
| Hair/bow/belt | Original rest rotations preserved through native updates; rigid attachment, with donor secondary motion still pending |
| Movement/combat | 568 original clips referenced by 846 source records and 9,258 cancel entries; source inputs, combo links, recoveries, reactions and solo animation graph |
| Attack collision/damage | Original attacking limb IDs drive sweeps from Jun's animated joints; normal damage read from the donor hit-data table |
| Hurtboxes | Character 23 receives the verified 14-sphere human profile; opponent hits reduce Jun's health |
| Body collision | The separate eight-sphere separation table now includes character 23; neither player can walk through Jun |
| Selector artwork | Recovered unused Tekken 3 arcade portrait and selector tile, converted to native PS1 palette layouts |
| Loading artwork | Recovered portrait used by the loading portrait decoder; original half-height loading tile adapted to PS1 team-card dimensions |
| Names/fonts | JUN descriptor, selector label and fight HUD; bitmap built from native glyphs; icon uploads moved out of the native font atlas |
| Effects | Menu palettes restore the resident effects colors before gameplay; model installation waits for native stage/actor initialization |
| Voices | All 12 original TTT1 Jun samples decoded from the verified C352 bank; attack, damage, KO and fourth voice category routed per actor |
| P2/mirrors | Separate per-player combat headers, alias tables, hit-stream pointers, GPU packets and texture pages |
| Throws/reversals | Original paired attacker/victim clips, throw locks, escape links, timed damage and releases |
| Victories | Both original solo victory clips, with original timed voice scripts; native round controller selects Jun's win/lose entries |
| Source conditions | Facing/camera conditions, contact groups, five opponent-specific hit records and 17 distance-dependent reaction records |
| Animation events | 36 original timed event scripts, source timed properties and character-confirmation facial expression |

The v4 converter no longer reads or copies Jin move templates. It imports the resolved TTT1 Jun solo graph, translates its fields and follows its reaction/throw/cancel destinations. Every exported solo condition has a handler; the audit reports zero unconverted conditions or unmapped destinations. The exporter rejects an unresolved solo destination, condition, property or transition instead of substituting idle or silently exporting a partial graph. Excluded rules belong to other characters, tag inputs/partners, or the TTT1 round controller, which is replaced by the PS1 round controller. Counts include common locomotion and victim reactions; they are not counts of unique attacks.

The original shared PS1 hit/locomotion records remain available to native fighters. Jun's alias adapter excludes donor attacks, but preserves destinations named by the native hit/paired-reaction tables and their terminal recovery chains even when the records live in the Jin asset bank. Those character-owned reaction records must not be replaced by idle. Common motions present in Jun's original TTT1 alias table are included as original Jun moveset data.

Non-Jun victims can use Jun's unique paired/hit clips, but imported common recovery IDs are translated back through `ALIA` to the receiving fighter's own native alias table. This applies to get-up and early crouch/movement cancels, not just idle; otherwise an opponent can follow a borrowed recovery's input links into Jun's attacks. Both Jun player slots retain their own full imported graph in mirrors. After the user requested live testing on September 19, the opponent throw fixtures passed with Jun in either slot, and the native crouch-cancel/attack fixture passed. Bounded checks also covered Heihachi and True Ogre recovering after the df1+2 input route; Hard difficulty and complete matchup coverage remain unverified. See `workspace/jun-import/MOVE_AUDIT_2026-09-19.md` for results and limitations.

The ordinary native fight camera is used during throws and victories. TTT1 camera-script IDs are a separate numbering system and are not copied into PS1 camera fields. Hair/bow/belt secondary physics, netplay and cross-process save states are outside this solo combat implementation. Live fixtures cover representative input chains and throw/reaction paths, not every possible combo, opponent and timing combination.

The voice tool verifies the local main-RAM capture, H8 sound program and C352 sample ROM, then extracts Jun's sound profile 19: seven attack samples (164â€“170), three damage samples (160â€“162), KO (163), and the fourth category (171). Original MAME sound commands confirmed all twelve wave addresses and playback frequency 0x18AF. The custom C352 mu-law decoder and interpolation produce 44.1 kHz mono PCM in a private `.juv` pack. An actor-specific host mixer preserves native shared effects, SFX/master gain, mute and reset behavior. Live attacks, damage, KO, paired throws and both solo victory scripts have been exercised. A natural throw KO reached the solo victory through the native round/replay sequence.

The combat pack is version 4, with a companion version 2 `.jst` reaction/event table pack. Damage comes from the ten-byte hit rows at 0x800EC8BC; attacking limb IDs are separate. Jun's jab has base damage 4 and becomes active at frame 10. The original MAME fixture lost 4 HP; the current native fixture strikes body zone 8 at 130% and loses 5 HP, matching the native hit-location calculation. Neutral high guard blocks the jab; the unblocked fixture uses a non-attacking dummy animation and checks that guard, counter and distance modifiers are absent. Both range-test and reaction-selector references are relocated: missing the range-test relocation previously selected an invalid reaction and animated the opponent as Jun's idle. Version 4 rejects older combat packs.

The jump follow-up preserves the signed horizontal-speed halfword at move-record `+0x16` when translating the hit index at `+0x14` into damage. Existing v4 packs lost that halfword: the runtime repairs their zero-speed directional jump entries using the loaded native jump profiles, retaining Jun's animations and frame windows. This compatibility repair is limited to jump aliases `7F..88`; it does not claim original TTT1 travel-distance parity. Corrected exports with nonzero source speeds are not overwritten. A September 19 live pad-input diagnostic observed forward/backward travel and return to idle, plus a nearly stationary neutral jump; both-side/costume/repeated-jump coverage is still pending.

The loader still reads a native Jin asset envelope to initialize PS1 structures. This is a compatibility dependency: Jun's selection, actor, model and moveset cache IDs remain independent. Native cached moveset headers stay intact; Jun uses private headers and per-player aliases.

The Practice UI regression was reproduced from a cold boot, without save-state loading. The first correction protected command icons and font palettes but placed costume tiles in the shared-effects region; player reports exposed the missing coverage. The current `tekken3_jun_texture_layout.h` packs individual TIM tiles into local `(0,0,64,224)` plus `(64,0,16,128)`, based at `(384,player*256)`. The latter is Jun's disabled native face-backup space. `tools/plan_jun_texture_atlas.py` generates the table and verifies every polygon lies within one source tile. Packet UVs, uploads, expression updates and immutable checks all follow that layout. Menu thumbnails use `(384,160)` / `(400,160)` only during menus, restoring native texture and palette contents at exit, including intervening native writes. Knocked-out thumbnails use a Jun-indexed grey palette at `(0,501)` instead of the native stock-portrait CLUT `(256,501)`; it is also restored at exit. This follow-up has offline checks only; gameplay is reserved for the user. `tools/test_jun_practice_ui.py` remains available for later explicitly requested cold-boot testing. The native move-list descriptions remain Jin's; Jun-specific move-list content is not implemented by this rendering fix.

## Three arcade outfits

Jun now has all three original TTT1 arcade outfits: blue denim, white waistcoat with black capris, and blue karate gi. Confirm Jun to open her three-entry carousel, browse with Left/Right or L1/R1, then press Cross/A to confirm the outfit. Circle/B returns to the roster. This also works for P2/CPU and without any HD skin pack enabled.

Direct cabinet selection uses **punch** for outfit 1, **kick** for outfit 2, and **Start / Enter** for outfit 3. In Team Battle, use **Square / Z**, **Cross / X**, and **Triangle / A** respectively; Start retains native random-team selection.

The importer extracts verified arcade models **46, 47 and 118**, with 26, 22 and 28 texture tiles and 168, 164 and 172 relocations. The expansion archive begins at model ID 102, so model 118 is member 16. `tools/data/jun_costumes.json` records source offsets, hashes and relocation maps. `tools/capture_jun_costumes.lua` can reproduce the relocation audit using a fresh MAME run and `JUN_CAPTURE_OUTFIT=1`, `2` or `3`.

Each outfit has a distinct native model cache ID. Both players retain their own packets, textures and combat state in mixed-outfit mirrors. Optional hair/bow/belt pieces follow the source model's presence, rest rotation and attachment parent. The native facial-copy table is extended with disabled entries for these models because Jun's own imported events upload her expressions; this prevents out-of-range native copies into faces or fonts.

`tools/test_jun_outfits.py --case direct` verifies all three native confirmations, actual palettes/texture tiles, accessories and real jab damage. `--case mirror` checks each outfit in both player slots, `--case team` checks Team Battle, and the legacy-named `--case gallery --renderer opengl` now checks the inline L1 carousel, advancing native timer and confirmations. These private fixture scripts load save states explicitly; normal play does not. Earlier gallery results describe the retired modal, not verification of the new carousel. Offline carousel checks are documented in `SELECTOR_CAROUSEL.md`.

## Reproduce from the verified local sources

```powershell
python tools/prepare_jun_import.py
python tools/ttt1_motion.py --validate-capture workspace/jun-import/jun-motion-poses.csv
python tools/convert_jun_moves.py
python tools/prepare_jun_ui.py
python tools/prepare_jun_voices.py
cmake -S . -B build-debug-server-lite -DTEKKEN3_JUN_EXPERIMENTAL=ON
cmake --build build-debug-server-lite --target psx-runtime -j 12
python tools/launch_jun_preview.py --selector --roster
```

Use the existing Windows toolchain configuration. `TEKKEN3_JUN_EXPERIMENTAL` defaults OFF for clean builds; both local build directories currently have it ON. Enabled builds stage the fifteen runtime assets into `mods/jun` and the local Jun package into `mods/packages`. The roster defaults on; `TEKKEN3_JUN_ROSTER=0` retains the older probe behavior. `TEKKEN3_JUN_ASSETS` remains an optional private-directory override. Source ROMs, captures, generated donor code and extracted assets remain private and ignored; original disc and executable source files are unchanged. The UI and voice tools and runtime verify their source/output hashes.

`jun/ui-report.json` records offsets and hashes for all five recovered source images: the large portrait, 68/58-row selector icons and 34/29-row loading icons. Both tall variants are preserved in the private pack; the native PS1 layouts use the 58-row selector and the adapted 29-row loading tile.

The arcade motion decoder yields 57 channels (polar root motion plus 18 XYZ joint rotations). An earlier comparison checked 976 poses / 30,036 channel values from 16 clips against MAME with zero mismatches. This sampled decoder check does not establish complete combat parity. `jun/combat-report.json` lists the conversion omissions.

## Validation

```powershell
python -m unittest tools.tests.test_prepare_jun_import tools.tests.test_ttt1_motion tools.tests.test_jun_combat tools.tests.test_jun_ui tools.tests.test_jun_voices tools.tests.test_fight_camera
python tools/test_jun_roster.py --case jun
python tools/test_jun_roster.py --case team --visible
python tools/test_jun_roster.py --case p2
python tools/test_jun_roster.py --case mirror
python tools/test_jun_roster.py --case jin --visible
python tools/test_jun_roster.py --case hit --visible
python tools/test_jun_roster.py --case jab
python tools/test_jun_roster.py --case push
python tools/test_jun_roster.py --case push-p2
clang tools/tests/jun_voice_test.c -I psxrecomp/runtime/include -o workspace/jun-import/jun-voice-test.exe
clang tools/tests/jun_ui_palette_test.c -I psxrecomp/runtime/include -o workspace/jun-import/jun-ui-palette-test.exe
python tools/test_jun_solo.py --case combos
python tools/test_jun_solo.py --case 24
python tools/test_jun_solo.py --case left
python tools/test_jun_solo.py --case right
python tools/test_jun_solo.py --case back
python tools/test_jun_solo.py --case command
python tools/test_jun_solo.py --case crouch-command
python tools/test_jun_solo.py --case reversal
python tools/test_jun_solo.py --case hit-followup
python tools/test_jun_solo.py --case victory --visible
python tools/test_jun_solo.py --case facing-victories --visible
```

The Python tests include synthetic format tests and private-fixture checks for relocation, motion decoding, damage, attacking limbs, command/condition translation, source-only transitions, throw damage timing, both victories, facial expressions, distance reactions, recovered graphics, names and voices. The C voice test checks category routing, independent players, gain, mute, clipping and resets. The palette test checks restoration across menu transitions while preserving native palette-animation and loader writes. The C pack validator rejects malformed references, unsupported pack versions and invalid limb IDs. Both native selector-layout test executables cover the expanded grids alongside stock grids and 4:3 behavior.

Native integration tests verify 22 unique cabinet IDs, navigation/confirmation, Jun's actor/model/cache identity, the four original basic attack clips, hair/bow rotations, 14 hurtbox radii, Team Battle through a fight, Jin versus Jun, Jun versus Jun, receiving damage, and the original jab with native hit-location scaling. Opponents in P2/mirror/jab cases are arranged through native loading globals; those cases do not test second-controller delivery. The jab and attack-input fixtures disable the CPU input generator; the receive-hit fixture leaves the opponent active.

Use `--visible` to validate actual widescreen output: headless mode does not engage the widened frontend. Historical visible captures were checked at 490x480 with 122 extra pixels. The native font region x896..943/y0..255 stayed byte-for-byte identical to the stock fixture in cabinet selection, loading and gameplay. Those captures predate the current per-tile packing and menu texture restoration; they are not verification of this follow-up. A historical texture probe also compared all 26 uploaded TIM images and palettes to the original export and found zero mismatches; every mesh's live UV/page/palette packet fields matched. The hair issue was a native accessory update replacing the source rotations with identity matrices.

Screenshots and machine-readable integration results are in `workspace/jun-import/roster-*`. `oracle-hit-data.csv` records the original arcade jab measurement (12-bit fractional health); `roster-test-jab.json` records the PS1 result (16-bit fractional health). A bounded directional/button/while-standing input sweep stayed in converted records with the opponent idle; this does not establish complete command-list coverage.

The September 13 VFX regression was reproduced as an opaque tan guard-spark rectangle. Jun's loading thumbnail overwrote CLUT 0x7DC4 in row 503, replacing the transparent entry with a skin color. Menu CLUT ownership is now scoped to selection/loading and restored before gameplay; the native guard palette is checked by the fight fixture. Delaying donor model uploads until native initialization also removed a colored strip in the top border across 24 OpenGL captures. Normal cold-start release/debug launches were tested without Jun environment overrides. Visible Team Battle, mirror matches and a 4 HP jab passed after these changes.

The body-collision regression was separate from damage hurtboxes: lookup 8003EC64 indexed the 22-entry table at 80096F60 with character 23 and read 0x0000000E as a pointer. The extended table supplies the stock human profile (240,96,96,300,120,120,120,120). Forward-input fixtures reproduced crossing before the fix and maintained positive separation afterward with Jun in either player slot.

Original TTT1 captures identify 1+3 as grab 0062DCC4, attacker 00757E64 and victim 00759D84; 2+4 uses attacker 0078EA44 and victim 0078FAF4. Both deal 30 HP, at original paired frames 145 and 90 respectively. These transitions and victim clips are now included. `tools/test_jun_solo.py` records live paired clips, damage, recovery, input chains, reversal contact, angled throws, command throws and victory playback into `solo-test-*.json`.

The current live cases cover 1,1 / 1,2 / 1,3 chains; both front throws; left/right/back throws (40/40/45 HP); b+1+2 (20 HP); the forward-crouch 2+3 throw (35 HP); a caught reversal; original hit reactions; both solo victories; and a source-only facing transition. The crouching throw requires 2+3 during the forward-crouch entry: holding down first produces a different attack in both the original MAME oracle and this port. Victory screenshots are captured during the animation, including a natural throw KO followed by the native replay/win sequence. `workspace/jun-import/solo-validation.json` ties the fixtures to their frozen executables and asset hashes.

The source-only facing transitions run after the native commit frame gate. Pushback table relocation uses a guarded generated variant of shard 04, preserving all overlapping alias bodies. Writing those instructions into guest RAM would divert the routine into the dirty-code interpreter and bypass its source-only native hooks; the build therefore leaves those guest instructions unchanged. The original shard is used when Jun is disabled.

Earlier bounded tests of the legacy stance/selection prototype passed repeated wins, losses, continue/game-over and stage reloads. Those results do not replace complete mode/replay/save-state regression coverage for this new roster. Cross-process imported-fight save states and netplay are not validated.

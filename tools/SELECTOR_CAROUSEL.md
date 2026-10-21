# Inline outfit carousel

P2 grid regression: `python tools/test_selector_native_guards.py` exercises the
actual native avatar/cursor/highlight loops against the runtime's exact-text guard.
The former resume-PC clipping admitted stock compiled loops after an interpreted
draw call; the next player then used the old seven-column table/stride. Changed
prefixes now prevent native handoff if the compiled continuation can loop back
into them. Straight tails remain eligible. The console selector is shared by VS,
Practice and Team Battle (screen 10), not just Team Battle.

`tools/inspect_live_selector.py PID MODULE_BASE` can inspect a user's running game
with VM_READ-only access; it never sends input, pauses, or writes guest state.

The normal selector and Team Battle use the same compact two-step host overlay.
Choose a character with any attack button (or Start in the normal selector).
That first press opens the carousel without committing a native costume. Left/Right
or L1/R1 browse; Cross/A confirms, and Circle/B or Select unselects the character.
Square/Triangle/Start also confirm inside the carousel. Release between steps;
held opening, confirming and cancelling buttons cannot spill into the next choice.
Only the controlling pad's directions/sticks are captured during the outfit step;
the guest and its timer keep running, and the other player's input remains live.
Team Battle's Start still randomizes at the roster, outside the outfit step.
Each team fighter remembers its own skin as actors rotate. Third-costume flags
are borrowed before the first injected input and restored after selection.

Controller ownership follows native state, not whether pad 2 is plugged in:
cabinet panel 8011864C + fighter*7C, phase 1 is human (own pad), phase 3 is CPU
(opposite pad); Team Battle 800B8D70 + fighter*AC, phases 2/3 are own-pad choices
and phase 7 is opposite-pad CPU choice. Cabinet identity comes from panel+1C,
not the saved last-used-character bytes. Native phase/team-count transitions stop
synthetic confirmation immediately. CPU cards appear on the CPU fighter's side.
Characters without a screenshot catalog use numbered original-costume cards,
including an unlocked third costume when the native unlock bit is set.

The standard selector starts at 99 instead of 20. Its verified SLUS-00402 overlay
initializer at 8010DD48..8010DD50 now computes 99 * tick_rate. Native decrement and
ceil(frames / tick_rate) display logic are unchanged. The patch applies even with
all optional skin/Jun mods disabled; it is gated by the Tekken-specific target and
the loaded overlay fingerprint. It changes neither the ROM nor saved options.

Rendering retains existing outfit-menu HDRGBA01 art at full source resolution.
Only bitmap lettering and borders use the 216x156 reference layout, with a
72x108 selected aperture and 56x84 neighbors at 480p. Portraits are center-cropped
to 2:3 and bilinearly sampled directly into their output-pixel dimensions, without
an intermediate thumbnail. The composition is cached until its content or size changes.
P1/P2 use equal edge margins inside the active game viewport, including letterboxed
windows. OpenGL and SDL/software share the exact rasterizer and placement helper.
All 27 shipped cards now use individually cropped user gameplay screenshots,
including Jun's three distinct costumes and the Eddy, Julia and Heihachi outfits.
If Jun artwork is missing, her private
native portrait remains a fallback labeled CHARACTER PORTRAIT; other missing art
remains a numbered usable card. No generated artwork is used. The experimental
Vulkan renderer is unchanged.

`tools/data/outfit_screenshot_crops.json` records each source screenshot number,
fighter side, exact native-resolution 2:3 crop and catalog identity. Reproduce with
`tools/import_outfit_screenshots.py --source-directory SOURCE --output-directory OUTPUT`.
The importer validates complete catalog coverage and exact pixel preservation,
and produces PNG/runtime RGBA pairs, a labeled contact sheet and hash audit.
Jun's model 52 is denim (source 5 left), model 53 is the white waistcoat
(source 4 left), and model 54 is the blue gi (source 4 right); this was checked
against the shipped costume texture banks and earlier model-identity capture.

## Offline verification

Compile `tests/outfit_carousel_test.c` with `-DTEKKEN3_LAUNCHER=1`,
`-I psxrecomp/runtime/include` and `psxrecomp/runtime/src/tekken3_outfits.c` from the
repository root. The old `outfit_slots_test.c` entry point forwards to this test.
It uses mock guest RAM, not a running game or save state, and checks:

- Guarded 99 initialization, no repeated countdown resets, and disabled-mod behavior.
- Two-step opening with every native costume button, held edges, Back, independent
  players, wrap and native directions outside the outfit step.
- CPU ownership from either pad, a disconnected opposite pad, distinct player/CPU
  skins, and no confirmation leakage between fighters.
- All Jun costumes, first-sample third-costume unlock and flag restoration.
- Stock/expanded team grids, team progression, Start handling and fighter skin swaps.
- Disconnect and all 131072 player/button combinations outside selection.

`tests/outfit_carousel_visual_test.c` adds the real rasterizer and shipped art.
Arguments are an executable asset base directory (with trailing slash) and an output
directory. It checks actual asset loading, exact portrait ratio, equal corner margins,
nonoverlap and bounds at 640x480, 960x720, 1280x720, 1920x1080 and 3840x2160, plus
source-resolution preservation, output detail and cache reuse. It produces PNG previews on a
plain background. Results are under `workspace/selector-carousel-qa`.

These tests passed and the release build succeeded. They do not substitute for
in-game verification of selector timing, transitions, Team Battle, or GL compositing.
The user is performing gameplay testing; normal startup opens the launcher without
loading a save state.

The keyboard regression (`tests/tekken3_keyboard_test.c`) links the real runtime
and launcher INI parsers against SDL without opening a window. Give it a copied
legacy `keybinds.ini` in a disposable directory; it exercises migration, every
cross-player key/stick, simultaneous keys, custom alts, unbinding and Reset.
It modifies only that test copy. Controller-assigned Tekken ports exclude
keyboard sources in `pad_sources_for`; explicit diagnostic dev-input merging
is unchanged. No gameplay testing was performed for this fix.

The main-menu regression now enforces the actual allocator alignment limit
and tests a nonzero low address half, plus interpreted entry without the
compiled wrapper. The earlier test stub incorrectly accepted 64 KiB alignment,
which hid the cause of the missing Quit option.

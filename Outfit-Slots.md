# Outfit selection

Launch `Play-Tekken3-Recompiled.cmd` and confirm a character to open its outfit
carousel. Choose the outfit separately; the first button no longer chooses a
costume. The timer continues from 99 and the game does not pause. Both players
and manually selected CPU opponents use this flow in normal and Team selectors.

| Control | Action |
| --- | --- |
| Any attack button on the roster | Select character and open outfit step |
| Left / Right, left stick, or L1 / R1 | Browse; wrap at either end |
| Cross / A (also Square, Triangle or Start) | Confirm the displayed outfit |
| Circle / B (also Select) | Unselect character and return to the roster |

Keyboard uses the mapped equivalents of those PS1 buttons. Release the character
button before confirming an outfit. Start on the normal roster opens outfits;
Start on the Team roster retains native random-team selection.

Each player now uses only their assigned device: keyboard bindings do not also
drive a controller-assigned player. P1's keyboard defaults are unchanged. P2's
defaults use I/J/K/L for movement, numpad 1/2/4/5 for Cross/Circle/Square/Triangle,
U/O for L1/R1, numpad Enter for Start and Backspace for Select. The exact old
duplicated P2 factory layout migrates on load; custom primary/alternate keys and
deliberately unbound maps are preserved. For two keyboard players with custom
maps, assign distinct keys in the launcher. The explicit diagnostic
`PSX_DEV_INPUT` override still merges devices; leave it unset for normal play.

Nina has three entries: **Purple Assassin**, **Crimson Leather**, and **White
Satin**. Anna has four: **Scarlet Silk**, **Midnight Silk**, **White Tiger**, and
**Jessica Rabbit**. Xiaoyu has four: **Red & Gold**, **Blue Ribbon**, **School
Uniform**, and **Cherry Blossom**. Kuma has three: **Brown Bear**, **Panda**,
and **Polar Bear**. Polar Bear adds white fur to Kuma's existing model while
retaining his red bandana and wristband. Both players can browse independently;
each player's choice is remembered per fighter. When one pad chooses a CPU, its
carousel appears on that CPU fighter's side without requiring a second pad.

With Jun imported, her carousel adds **Blue Denim**, **White Waistcoat**, and
**Karate Gi**, using the three original TTT1 arcade meshes and texture sets.
Her carousel also works without any HD skin pack. Native costume confirmation
buttons are emitted internally only after the chosen card is confirmed.

Missing or disabled HD packs remove their custom entries. Original costumes
remain available, using numbered cards for fighters without supplied screenshots.
No combat inputs are changed.

The menu supports local OpenGL and SDL/software play. Its host choices are not stored inside old
PS1 save-state files: loading a match uses the host cosmetic choice currently
confirmed in this process. New launches start with the original costumes.

## Artwork

Additional OpenGL skin packs:

- **Heihachi — Tiger Coat:** fine gold/black tiger stripes, dark fur and plain charcoal
  clothing on his original alternate coat model.
- **Eddy — Monochrome:** primary outfit in black and white, with black hair.
- **Julia — Blue Turquoise:** blue/turquoise clothing, dark denim and silver-white
  boot details, adapted to her original primary model.

These are texture adaptations, not imports of the later-game reference meshes.
Their stock outfits remain in the carousel (including Tiger Jackson for Eddy).
They work through the same P1/P2/CPU/Team selection flow. Disable each independently
in the launcher Mod Manager; restart to apply. New cards use labelled fallbacks
until the player supplies in-game screenshots—no generated carousel portraits.
They use OpenGL like the existing HD skin packs; the software renderer retains
stock textures. Gameplay, skeletons, disc data and textures outside the body
ARC member are not modified.

Texture artwork was made with built-in `image_gen`, using the original UV sheets
and supplied costume references. Exact prompts are saved in
`tools/data/new_skin_art_prompts.json`; pack inputs and outputs live under
`mods/assets/eddy-monochrome`, `mods/assets/julia-blue` and
`mods/assets/heihachi-tiger-coat`. Rebuild these packs with
`python tools/new_character_skin_pack.py`; validate exact pixel/palette guards
and cross-character rejection with `python tools/test_new_character_skins.py`.

Heihachi revision 2 uses `mods/assets/heihachi-tiger-coat/authored-atlas-v2.png`,
with the exact built-in image-generation prompt in
`tools/data/heihachi_tiger_coat_v2_prompt.json`. It removes the large gold trouser
motifs, uses finer stripes and dark shoe textures, and excludes the mixed
skin/cuff tile entirely along with all face, hair and bare-skin tiles. The first
authored atlas is retained as a source backup but is no longer packed. The body
member contains 33 TIMs; a fixed 30-texture exclusion previously missed the last
eight. Tiles 25–31 now reuse the existing shoe, tiger cloth and fur artwork,
with UV rotation placing trim along the bottom of the coat hems. Tile 32's
small dark button detail stays stock. There are 21 replacements per player,
42 guarded map entries total, in a 1152x1728 atlas. The packer and inspection
tool now derive body membership from actual ARC boundaries.
Offline tests cover all 80 newly mapped retail clothing polygons, the preserved
button polygons, both player placements, UV bounds and cross-skin rejection.
Offline mapping checks and release staging passed; final appearance still needs
the player's in-game check on the original PS1 geometry.

All 17 photo cards use the user's real in-game screenshots, cropped individually
to 2:3 with the full fighter visible and the HUD/opponent excluded. PNGs and
runtime RGBA copies are in `mods/assets/outfit-menu`. Source pixels are preserved,
not synthesized or upscaled. Exact mappings/crop coordinates are recorded in
`tools/data/outfit_screenshot_crops.json`. Full-resolution crops are sampled
directly at the card's displayed size; they are not reduced to 72x108 first.

## Extending the menu

`mods/assets/outfit-menu/catalog.txt` supplies the rows; the renderer always
shows a scrolling three-card view and computes the total from the catalog.
No menu layout code needs to change to add more entries. Each row is:

```
id|character ID|display name|stock confirmation mask in hex|skin ID|art basename
```

Stock confirmation masks: `8000` = punch outfit, `4000` = kick outfit,
`0008` = third outfit. Skin ID `-1` uses original textures; the registered HD
packs currently use `0` = Nina, `1` = Xiaoyu, `2` = Anna, `3` = Kuma,
`4` = Eddy, `5` = Julia and `6` = Heihachi. A new HD atlas needs
its own renderer pack registration in addition to a catalog row. IDs and art
basenames use letters, digits, hyphens or underscores. Duplicate IDs and
malformed rows are ignored. Missing art keeps a usable labelled card; a
missing/empty catalog falls back to the built-in entries.

Put a 2:3 PNG under the matching art basename and run:

```
python tools/outfit_menu_pack.py
```

Build the runtime to stage the catalog and artwork beside the executable.
Restart the game to reload them.

## Implementation and verification

`tekken3_outfits.c` owns selection, cancellation, player isolation and finite
confirmation pulses. Guest VBlank ticks, rather than controller poll count,
time those pulses, and native phase changes stop them immediately. The guest
continues running throughout selection. Directions and analog sticks are
captured only for the fighter whose outfit is being chosen.

The cabinet fighter identity is at panel `0x8011864C + fighter*0x7C`, offset
`0x1C`. Native phases determine whether its own or the opposite controller is
choosing it. The original third-costume
selection handler at `0x8010DAE0` tests bit(character) of `0x80097EF4`.
The gallery temporarily supplies only a missing bit needed for a selected
third costume, then restores it after selection; it preserves the other
unlock/progress bits. Original texture and palette guards remain active.

`tools/tests/outfit_slots_test.c` covers two-step confirmation, Back, held
buttons, both players, CPU ownership from either pad, Team Battle, missing packs,
third-costume flags, and unchanged combat input for all 65,536 words on both pads.
The visual test checks all 17 photos and layout from 480p through 4K.
See `tools/SELECTOR_CAROUSEL.md` for the current offline verification scope.
Older live gallery results predate this two-step flow; gameplay confirmation
of this change is left to the user.
The debug-only `outfit_screenshot` command captures the actual host gallery,
which is outside the guest framebuffer used by ordinary screenshots.
Kuma's three live selections and match captures are recorded separately in
`out/kuma-skin/gallery-validation.json`. The focused Kuma tests cover stock
punch/kick selection, both player choices, custom-pack availability, exact
4bpp pixel/palette matching, Panda rejection and preserved accessories.

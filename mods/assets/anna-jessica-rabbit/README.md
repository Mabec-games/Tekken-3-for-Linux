# Anna Jessica Rabbit

Jessica Rabbit inspired textures for Anna Williams's original red evening
gown: crimson sequins, lavender satin opera gloves, copper-red hair, green
eyes with violet eye makeup, red lips, bare-looking legs and red heels.

Start `Play-Tekken3-Anna-Skin.cmd`, highlight Anna and press L1. Browse to
**Jessica Rabbit** with Left/Right, then select with Cross, Square or Enter.
The original red gown, blue gown and White Tiger costume have separate cards.
The **Anna — Jessica Rabbit** extra outfit is enabled by default under
Character Skins in the Mods catalog. Restart after toggling it. OpenGL is
required. Nina White Satin, Xiaoyu Cherry Blossom Ribbon and Forest HD can
remain enabled together.

This is a texture adaptation on Anna's original model. Her bob haircut,
facial proportions, dress length and elbow bows retain their original shape;
it does not add Jessica's longer hairstyle or a replacement character mesh.
Animations and gameplay are unchanged. The blue gown and tiger outfit stay
available. A per-player red-costume identity check prevents shared hair and
leg textures from partially changing the blue gown.

The visual reference was an original Walt Disney Studios production color
model cel from *Who Framed Roger Rabbit* (1988), reproduced by RR Auction:
https://www.rrauction.com/auctions/lot-detail/345114806201019-jessica-rabbit-production-color-model-cel-from-who-framed-roger-rabbit/

`authored-atlas.png` was edited with the built-in image generation tool using
the locally extracted Anna UV atlas. The complete prompt and reference are in
`prompts.json`. `tools/anna_skin_pack.py` only crops, resamples and pads these
authored cells, then fingerprints the verified local source textures.

The 1152 x 1152 atlas uses about 6.75 MiB with mipmaps. All 32 texture entries
check original pixels and 16- or 256-color palettes, covering both players.
The original guest textures control transparency and lighting. The game disc
and model data are not changed. Files remain in this local installation.

Rebuild from verified US BNS 217:

```powershell
python tools/anna_skin_pack.py --source workspace/anna-skin/records/217.arc --art mods/assets/anna-jessica-rabbit/authored-atlas.png
```

For a temporary original-costume comparison, set `PSX_ANNA_SKIN=0` before
launch. This leaves the other skin and stage packs enabled.

Validation covers live Anna versus Jin gameplay, original pixel/palette
identities against captured VRAM, both player placements, rejection of the
blue gown's shared textures, cross-skin rejection with Nina and Xiaoyu,
independent invalidation and the forest matcher regression. In-game preview:
`out/anna-skin/after.png`, normalized to the intended 16:9 pixel aspect.

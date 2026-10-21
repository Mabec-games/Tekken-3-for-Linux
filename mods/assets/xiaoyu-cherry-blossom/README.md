# Xiaoyu Cherry Blossom Ribbon

Xiaoyu's original red-and-yellow ribbon outfit becomes rose-pink silk with
powder-blue waist ribbons, matching hair ties and collar trim. Pearl-white
cherry blossoms and pale-blue embroidery decorate the body panels and trouser
hems. The shoes have coordinated pink edging.

The **Xiaoyu Cherry Blossom Ribbon** built-in package is enabled by default.
Highlight Xiaoyu and press L1, browse to **Cherry Blossom** with Left/Right,
then select with Cross, Square or Enter. Original outfits have separate cards.
Toggle **Xiaoyu — Pink Silk and Blue Ribbons** in the
Mods catalog under Character Skins, then restart. The OpenGL renderer is
required. It works alongside Nina White Satin and Yoshimitsu Forest HD.

The 1152×1152 texture atlas uses about 6.75 MiB including mipmaps. All 30
replacement guards verify both original pixels and palettes, with separate
placements for each player. Face, hair, original skin-only tiles, effects,
model geometry, transparency, animations and gameplay retain their original
behavior. The hair ties reuse the new blue ribbon material.

`authored-atlas.png` was edited with the built-in image generation tool using
the locally extracted garment atlas. The complete prompt is in `prompts.json`.
`tools/xiaoyu_skin_pack.py` splits and pads the generated cells and creates the
verified texture mapping; it does not generate artwork. These files are kept
in this local installation.

Rebuild from locally extracted, verified US BNS 129:

```powershell
python tools/xiaoyu_skin_pack.py --source workspace/xiaoyu-skin/records/129.arc --art mods/assets/xiaoyu-cherry-blossom/authored-atlas.png
```

For a temporary original-costume comparison, set `PSX_XIAOYU_SKIN=0` before
launch. This does not disable Nina or the forest pack.

Validation: actual Xiaoyu vs Eddy match, approximately 60 FPS; original stock
identities checked against live VRAM; both player placements, cross-skin
rejection and independent map invalidation checked for Xiaoyu and Nina; forest
matcher regression passed. Actual in-game preview: `out/xiaoyu-skin/after.png`
(normalized to the display's intended 16:9 pixel aspect).

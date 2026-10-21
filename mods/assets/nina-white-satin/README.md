# Nina White Satin

Nina's trouser costume now has an ivory-white satin top, black hair, dark
black leather trousers, and cherry-red patent high heels. Highlight Nina and
press L1 to open the gallery, browse to **White Satin** with Left/Right, then
select with Cross, Square or Enter. Both original costumes have their own
cards; the ordinary roster still accepts the original costume buttons.

The built-in **Nina White Satin** package exposes an extra outfit by default. Toggle
**Nina — White Satin and Red Heels** under **Mods → Character Skins**, then
restart. Requires the OpenGL renderer. It works alongside Yoshimitsu Forest HD.
For a temporary original-costume comparison, launch with `PSX_NINA_SKIN=0`.

The 1728×864 host atlas uses about 7.6 MiB with mipmaps. Exact pixel and palette
fingerprints limit replacement to the verified US Nina trouser costume, with
separate guards for each player slot. Original transparency, lighting, UVs,
model geometry, animation and gameplay remain authoritative. This is a texture
skin on the original model, rather than a new character mesh.

`authored-atlas.png` was edited with the built-in image generation tool using
the locally extracted costume atlas. The prompt is recorded in `prompts.json`.
The packaging script only splits, resamples and pads those generated tiles;
no generative work is performed in the script. The locally derived face/skin
reference art and resulting atlas are kept in this local installation.

Rebuild from the verified local BNS 117 record:

```powershell
python tools/nina_skin_pack.py --source workspace/nina-skin/records/117.arc --art mods/assets/nina-white-satin/authored-atlas.png
```

Validation: actual Nina vs Yoshimitsu forest match; original texture and
palette identities verified from live VRAM; all 26 guards checked for both
player placements; wrong-fighter and modified-palette rejection; original
forest matcher regression tests. See `out/nina-skin/after.png` for an actual
in-game image, normalized to the intended 16:9 pixel aspect for presentation.

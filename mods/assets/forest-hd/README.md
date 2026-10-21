# Yoshimitsu Forest HD — experimental 1.0

The forest background and moss ground use newly authored host GPU textures.
Launch `Play-Tekken3-Recompiled.cmd` as usual. The **Yoshimitsu Forest HD** mod
is enabled by default. To turn it off, open `Configure-Tekken3-Recompiled.cmd`,
disable **HD Forest Background and Ground** in Mods, and restart the game.
OpenGL is required; other renderers retain the original assets.

The background is 2172 × 542 usable pixels and the ground is 1254 × 1254.
The host textures occupy approximately 14 MiB including mipmaps, with up to
8× anisotropic filtering. Geometry, collision, fighters and gameplay are stock.
The full wraparound backdrop is mapped from the original stage mesh rather
than stretched across the screen. Some original geometry seams and horizon
cutouts remain. This is an experimental texture remaster, not new 3D geometry.

The PNG artwork was made using the built-in image-generation tool; see
`prompts.json`. The background's generated letterboxing is omitted when
compiling its RGBA payload. The `.rgba` files and `mapping.bin` are loaded at
startup. Restart after changing them.

No disc or guest asset is overwritten. The texture map checks both the
original tile and the final shared CLUT before substituting a texture.
Mismatches fall back to the original rendering. `PSX_HD_TEXTURES=0` is a
temporary developer override to disable substitutions without changing Mods.

Recompile after extracting the verified US BNS records 038 (textures) and
058 (stage model) into a private workspace:

```powershell
python tools/forest_hd_pack.py --textures workspace/forest-research/records/038.arc --model workspace/forest-research/records/058.bin
```

The builder requires Pillow and NumPy, verifies both records' SHA-256 values,
and writes only fingerprints, UV transforms and authored pixel data into the
runtime pack. The original ARC and model are private build inputs.

Validation: release and debug builds, live forest gameplay and camera changes,
stock-versus-HD captures, and a standalone C matcher test covering identity,
palette changes, invalidation, bounds and malformed pack rejection. Stable
forest gameplay samples ran around 60 FPS on this PC at the existing 3×
internal resolution. Startup and save loading can cause brief stalls.

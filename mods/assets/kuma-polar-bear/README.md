# Kuma: Polar Bear

Highlight Kuma and press **L1** (keyboard **Q**). Browse to **Polar Bear** and
confirm. Brown Bear and Panda remain original outfits in the same three-card
gallery. Each player chooses independently. Restart the game after updating.

This OpenGL texture skin gives Kuma detailed ivory-white fur and a dark nose,
using his existing model and animations. His red bandana, wristband, studs,
and claw textures remain original. It adds no polygonal fur or new bear mesh.

The package is enabled by default. Disable `tekken3.skin.kuma-polar-bear` in
the mod configuration, or launch with `PSX_KUMA_SKIN=0`, to remove its custom
entry. The other two costumes remain available.

The 1152x1152 atlas has 16 padded cells. Only 11 fur/face cells are mapped,
with separate exact pixel and 16-color palette guards for both player slots
(22 map entries). The stock source is BNS record 161, SHA256
`bc2159f986181c6f6c99ad145bf3aaa7d6639e3dcffef11c934d9caa5d8f3921`.
Panda's separate texture record is explicitly tested for rejection.

Rebuild from the project root:

```
python tools/kuma_skin_pack.py --source workspace/kuma-skin/records/161.arc --art mods/assets/kuma-polar-bear/authored-atlas.png
```

Built-in image_gen produced the atlas and Panda/Polar Bear splash paintings.
Base Kuma uses the user-selected Project Fighters `Loading Screen/Kuma.png`
as an exact copy. All three splashes are 1024x1536.
Exact prompts, read-only references, generated source paths and hashes are
recorded in `workspace/kuma-skin/prompts.json`. Splash PNG/RGBA files are
in `mods/assets/outfit-menu` under the `kuma-` prefix.

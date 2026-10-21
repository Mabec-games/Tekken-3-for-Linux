# Tekken 3 launcher

Open `Play-Tekken3-Recompiled.cmd`, or run `build-release/Tekken_3_Recompiled.exe`.
The launcher appears before normal game startup, including when an older settings
file has `skip_launcher = true`. It waits for **LAUNCH GAME**; closing it does not
start the game. This frontend is for the Recompiled executable, not the separate
experimental `Tekken_3_PC_Port.exe` product.

## Pages

- **Play:** selected disc, player input sources, and enabled feature count.
- **Mod Manager:** the real mod provider, with `.psxmod` installation, feature
  toggles/options, installed packages, versions, and compatibility diagnostics.
  Activation changes apply on launch. Invalid plans return to Mods with the error.
- **Keyboard:** independent P1/P2 primary and alternate keys, clear, and confirmed
  reset. Tekken's four attack buttons are labeled. Editing keys does not change
  the player's active device or their gamepad profile. Key edits save immediately.
- **Controller:** device selection, saved/offline devices, per-device button/axis
  bindings, deadzone, rename, Map All, and Save Profile. Existing capture code
  accepts only the selected controller and waits for release between mapped inputs.
- **Disc Library:** attach/select/recheck/detach local CUE, BIN, ISO, or CHD images.
  Select CUE for multi-track discs. Image Setup exposes the existing preparation
  workflow when needed; attaching a file does not make an unsupported image playable.
  Only verified Tekken 3 USA (`SLUS-00402`) can launch in this build.
- **Settings:** display, audio, system, and hotkeys. **Memory Cards:** native save
  slot management. Existing online functionality appears only in supporting builds.
- **Patches & Updates:** installed patch version and notes, manual GitHub check,
  automatic boot-check preference, available-version button, and in-launcher
  download progress. The first launch asks whether to enable boot checks; the
  setting can be changed here at any time. Installing always needs a button click.

## Updating

The updater checks published releases at
`Tekken 3 for Linux`, including the project's prereleases. It
compares numeric `vMAJOR.MINOR.PATCH` versions and selects only a newer full
`Tekken3Recompiled-vMAJOR.MINOR.PATCH-Easy-Setup.zip` with a matching
`RELEASE-MANIFEST.json`. A Setup Fix ZIP is never treated as a full update.
GitHub's asset SHA-256 digests and every file in the manifest are checked before
any installed file is changed. Downloads and verification run while the native
launcher displays progress. It then closes, installs the files, rebuilds the
game using the saved first-setup inputs, and reopens the launcher. The existing
disc image, `.setup` state and downloads, local mods, saves, and generated
game data stay in place. If the rebuild fails, the previous source files,
game executable, runtime mod/assets folders, and ready state are restored.

The official v0.1.2 Easy Setup archive predates this feature, so players on
v0.1.2 need to install a newer Easy Setup package once. Later full releases can update
from inside this launcher. Package future releases with
`scripts/create_easy_setup_release.py` and publish the generated ZIP,
`RELEASE-MANIFEST.json`, and `SHA256SUMS.txt` together. The package builder
uses the SHA-256-pinned v0.1.2 archive only for its bundled Python runtime and
bootstrap; it overlays this checkout's current game and launcher source.

The library stores references and the selection in `disc-library.txt` beside the
executable. Detach asks for confirmation, never deletes image/track files, and is
remembered even if you exit without playing. An explicit `--disc` overrides the
remembered selection initially; a later selection in the launcher wins on launch.
Damaged library files are not overwritten. The library is capped at 64 images and
the native 512-byte path capacity; paths containing spaces are supported.

Input and mod data keep their existing runtime formats (`keybinds.ini`, per-GUID
`input.ini`, and the mod provider's profile). No separate mapping engine is added.
Developer fixtures retain explicit `--no-launcher` / `--headless` bypasses. The
normal play shortcut no longer uses a bypass or forces a fixed disc path.

## Visuals and build

Game-owned layout/theme live in `src/tekken3_launcher_ui.inl` and
`src/tekken3_launcher_theme.h`, enabled with the target-only `TEKKEN3_LAUNCHER`
definition. The frontend is native SDL/ImGui, with a charcoal/red/aged-gold palette,
compact menu rows, and the shipped PlayStation controller artwork. No generated
character art, browser runtime, or remote assets are required.

Headings use unmodified [Rajdhani Bold](https://github.com/google/fonts/tree/main/ofl/rajdhani),
not a purported original Tekken font. Its SIL OFL license and attribution ship with
the font in `launcher_assets/fonts` and the built `assets/fonts` directory.

## Verification

Release build passed. Isolated native framebuffer checks covered 1280×820 and
960×640, all main pages, a real keyboard capture with a saved controller selected,
reopening the key mapping, and resetting keys without changing the controller map.
Feature toggling changed the home-page enabled count. Detaching the selected disc
disabled launch, left the original CUE present, and remained detached after reopening.
Old skip settings and `PSX_NO_LAUNCHER=1` did not bypass normal startup.

The standalone `tools/tests/tekken3_disc_library_test.cpp` covers normalized duplicate
paths, Unicode reference persistence, missing files, remembered selection, last-image
detachment, and damaged-file protection. Local screenshots/logs are under
`workspace/launcher-qa-20260919-233504` (not distribution assets).

No match was started. Physical controller capture/hotplug, archive installation,
CHD preparation, online play, and launcher-to-game handoff still require manual
confirmation; their existing backend implementations are reused.

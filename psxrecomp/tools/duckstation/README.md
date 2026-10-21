# DuckStation oracle (dynamic comparison harness)

PSXRecomp v4 uses a patched build of [stenzek/duckstation](https://github.com/stenzek/duckstation) as a live oracle for the recompiled BIOS. Our runtime speaks JSON-over-TCP on port **4370**; the patched DuckStation speaks the same protocol on **4371**, so tools like `debug_client.py compare` can diff live state between the two at any moment.

## Layout

- **`duckstation/`** (git submodule) — pristine upstream DuckStation source tree, pinned to commit `ffb33c281d196eb8ee0f559085ca285de7cdd51b` (release-20260328 era). Never edited directly.
- **`tools/duckstation/psxrecomp_oracle.patch`** — our changes as a unified diff against the pinned upstream base. Touches 7 files (~1200 lines). Adds `src/core/psxrecomp_debug_server.{cpp,h}`, wires `PSXRecompDebug::Initialize(4371)` into `System::Initialize`, exposes three GPU debug accessors, registers a log channel.
- **`tools/duckstation/setup.sh`** — idempotent. Initializes submodule, fetches + verifies + extracts prebuilt Windows deps (SDL3, Qt6, ffmpeg, …), normalizes the absolute paths baked into the prebuilt CMake metadata, applies the oracle patch.
- **`tools/duckstation/build.sh`** — runs CMake (Visual Studio 17 2022, x64, Release) and MSBuild on `duckstation-qt`. Requires the Visual Studio 2022 "Desktop development with C++" workload (CMake + MSBuild come with it).
- **`tools/fix_duckstation_deps_paths.py`** — helper used by `setup.sh` to rewrite stale `_IMPORT_PREFIX` values in the extracted prebuilt deps.

## First-time setup

```bash
cd <psxrecomp-v4>
bash tools/duckstation/setup.sh     # ~5 min: clone submodule + fetch/extract deps + apply patch
bash tools/duckstation/build.sh     # ~15-30 min: compile duckstation-qt Release x64
```

The resulting binary is at `duckstation/build/bin/duckstation-qt.exe`. Launch for headless oracle use:

```bash
./duckstation/build/bin/duckstation-qt.exe -bios -nogui -fastboot &
# Wait ~5s for BIOS boot, then:
echo '{"cmd":"ping"}' | ncat -w2 localhost 4371
```

## Regenerating the patch

If our oracle changes need to be updated, edit files in `duckstation/` directly, then regenerate the patch against the pinned upstream base:

```bash
cd duckstation
git diff ffb33c281d196eb8ee0f559085ca285de7cdd51b > ../tools/duckstation/psxrecomp_oracle.patch
```

The pinned base SHA lives in one place only: `UPSTREAM_BASE` at the top of `tools/duckstation/setup.sh`. Update it there if we ever rebase onto a newer upstream commit.

## Why this layout (vs a hosted fork)

- Keeps the upstream source untracked in v4's git history — no 2.1GB of upstream code in our blame.
- Keeps *our* 1200-line patch reviewable as a single text diff in `tools/duckstation/` — in-tree, versioned, diffable across sessions.
- Matches the nestopia setup in sibling project `<nesrecomp>/runner\nestopia_cmake.cmake` + `runner/nestopia_oracle.patch`. Same mental model: submodule upstream, patch on top, auto-apply at setup time.
- No private/public GitHub fork to maintain or keep in sync.

## Protocol parity with native runtime

Both servers implement the same JSON-over-newline command set where possible so that `tools/debug_client.py compare <cmd>` diffs state between them. See `TCP_COMMANDS.md` at the v4 root for the full command table with "native-only / duckstation-only / both" annotations.

## First-time setup: the `duckstation-qt.rcc` resource file

The MSBuild `duckstation-qt` target does NOT include the Qt resource compile
step. You must also build the `duckstation-qt-rcc` target, which produces
`build/bin/resources/duckstation-qt.rcc` (~740 KB). Without it the binary
opens a dialog `"duckstation-qt.rcc could not be loaded. Your installation is
not complete."` and exits. `tools/duckstation/build.sh` builds both targets;
do not short-cut to `-t:duckstation-qt` alone.

After the rcc is in place, a **first-time GUI launch** is also required so
DuckStation's setup wizard can write out a working `settings.ini`. Launch
without any command-line flags:

```bash
python3 tools/launch_ds_detached.py   # spawns GUI, no flags
```

Click through the wizard (BIOS directory → pick `duckstation/build/bin/bios/`,
then continue, then quit). After that, headless launches work forever:

```bash
python3 tools/launch_ds_detached.py -bios -nogui -fastboot
```

Verify with a quick ping:

```bash
NC='/c/Program Files (x86)/Nmap/ncat'
(printf '{"cmd":"ping"}\n'; sleep 1) | "$NC" localhost 4371
# expect: {"id":0,"ok":true,"frame":N}  with N > 0
```

The settings.ini that the wizard writes is needed but not tracked (it's under
the gitignored `duckstation/build/`). If you rebuild from scratch (clobbering
`build/`), repeat the GUI-first-launch once.

## Troubleshooting

- **"oracle patch does not apply cleanly"** — either upstream commit has been moved past the pinned base (check `git -C duckstation log --oneline -1`), or the patch file was regenerated against a different base. Fix by either resetting the submodule to `$UPSTREAM_BASE` or updating the pin.
- **"sha256 mismatch" on deps archive** — the prebuilt deps version in `duckstation/dep/PREBUILT-VERSION` has been bumped. Either update `PREBUILT_SHA256` in `setup.sh` to the new hash from `duckstation/dep/PREBUILT-SHA256SUMS`, or pin the submodule to an older commit that expects the cached archive's version.
- **"UNSUPPORTED CONFIGURATION" warning from DuckStation CMake** — cosmetic. The upstream build system prefers `msbuild` driven via a VS solution (which is what `build.sh` does). The warning fires any time CMake runs on Windows; safe to ignore.

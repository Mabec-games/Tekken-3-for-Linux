# New Project Layout + Project Studio

Scaffold **new** titles and **migrate** older ones onto the setup-host layout.

**Policy:** public releases are **setup-host only** (no prebuilt generated game C).

## New project

```bash
sh tools/new_project_layout/setup_project.sh --disc /path/to/game.cue --dir ~/src
```

See [`docs/GAME_PROJECT_SETUP.md`](../../docs/GAME_PROJECT_SETUP.md).

## Project Studio (migrate / update)

Shared Python library under `project_studio/` with CLI + tkinter GUI.

```bash
# Audit layout gaps
python3 tools/new_project_layout/migrate_project.py audit \
  --root /path/to/ApeEscapeRecomp

# Show ordered plan
python3 tools/new_project_layout/migrate_project.py plan \
  --root /path/to/ApeEscapeRecomp

# Dry-run apply (recommended first)
python3 tools/new_project_layout/migrate_project.py apply \
  --root /path/to/ApeEscapeRecomp --dry-run

# Apply for real (rewrites CMake with .pre_migrate.bak)
python3 tools/new_project_layout/migrate_project.py apply \
  --root /path/to/ApeEscapeRecomp \
  --disc /path/to/game.cue

# GUI
python3 tools/new_project_layout/migrate_project.py gui
# or
python3 tools/new_project_layout/project_studio_gui.py
```

### Ops (subset)

| Op | Purpose |
|----|---------|
| `rename_psxrecomp_submodule` | `psxrecomp-v4` → `psxrecomp` |
| `ensure_recomp_ui_submodule` | Add `recomp-ui` |
| `emit_codegen_setup` | Thin `codegen_setup.c/.h` |
| `rewrite_cmake_setup_host` | `psxrecomp_add_game_runtime` + wizard |
| `emit_packager` | `scripts/package_setup_release.sh` |
| `emit_ci_workflow` | Setup-host `release.yml` |
| `probe_disc_refresh` | TOC / catalog / seeds (needs `--disc`) |
| `annotate_legacy_packaging` | Mark old prebuilt packagers obsolete |

Wizard + `recomp-ui` are forced on for `apply` (setup-host requirement).

Helpers reused: `probe_disc.py`, `fill_tokens.py`, `sync_symbols.py`, `templates/*`.

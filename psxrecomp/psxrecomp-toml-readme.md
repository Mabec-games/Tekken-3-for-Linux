# psxrecomp-toml 🛠️🎮

`psxrecomp-toml` is a companion tool designed to streamline the configuration process for `psxrecomp` static recompilation projects. It analyzes a PlayStation 1 executable (`psx-exe`), automatically extracts key deployment metadata, and generates a valid `game.toml` configuration along with initial function jump seeds (`JAL` targets).

No more digging around with Hex Editors or Ghidra just to find the entry point, load addresses, and basic text sizing.

## Features

- **Automated `game.toml` Assembly:** Dumps necessary headers including `load_address`, `entry_pc`, and `text_size` based on the binary's actual PS-X EXE structure.
- **Static Discovery Disambiguation:** Scans for standard jump-and-link (`JAL`) destination blocks.
- **Coverage Tuning:** Includes edge-case address mapping right after subroutine returns (`jr $ra`) to capture maximum layout structure out-of-the-box.

---

Usage: psxrecomp-toml <PS1-EXE> [options]

Options:
  --output <path>            Write game.toml to <path> (default: stdout)
  --seeds <path>             Also write JAL-target seed file to <path>
  --name <str>               Game name in TOML (default: derived from EXE)
  --id <str>                 Game ID (default: auto-detect or empty)
  --stdout                   Force output to stdout even with --output
  --include-after-return     Add addresses after jr $ra to seeds (more coverage,
                             may include some data addresses)
  -h, --help                 Show this help
  
### Example Workflow

psxrecomp-toml ./isos/SCES_028.34 \
  --output ./projects/CrashBash/game.toml \
  --seeds ./projects/CrashBash/recompiler/seeds/seeds.txt \
  --name "Crash-Bash-EUR"
  
  
#### ⚠️ A Note on Seed Coverage

While psxrecomp-toml does the heavy lifting by scanning code segments and extracting immediate jump addresses for you, it does not statically resolve 100% of the game's execution paths (such as dynamic function tables or indirect register dispatches).

If the recompiler throws dynamic discovery gaps or unknown dispatches later during active runtime simulation, you will still need to feed those newly discovered addresses back into your seeds.txt manually to close the gap.

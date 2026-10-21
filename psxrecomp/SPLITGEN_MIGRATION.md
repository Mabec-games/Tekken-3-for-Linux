# Split-gen migration (parallel-compilable generated C)

The recompiler now emits the generated game code as **multiple parallel-
compilable translation units** instead of one monolithic `<serial>_full.c`:

- `<serial>_decls.h` — shared declarations (runtime extern prologue,
  `static inline` unaligned helpers, all `func_*` + `psx_alias_body_*`
  forward declarations).
- `<serial>_full_00.c … _NN.c` — function-body shards (~40k lines each),
  each `#include`ing the decls header.

Alias-group host bodies (`psx_alias_body_*`) are now **externally linked**
so shards have no atomicity constraint. `runtime.cmake`'s
`GAME_GENERATED_FULL_C` is **multi-value** (a single path still works, so
this is backward compatible until a game regenerates).

Measured on Tomba: 41 MB single TU → 36 shards; `-O3` compile
**4m35s → 51s** (`-j16`, ~5.4×). Generated function bytes are unchanged.

## Migrating a game to the split output

A game keeps building on its existing monolithic `<serial>_full.c` until it
is regenerated against this framework. When you regenerate a game, make one
CMake change so it compiles the shards:

Replace the single generated-full path, e.g.

```cmake
set(GAME_GENERATED_FULL "${CMAKE_CURRENT_SOURCE_DIR}/generated/<serial>_full.c")
```

with a glob that matches both the (transitional) monolith and the shards:

```cmake
file(GLOB GAME_GENERATED_FULL CONFIGURE_DEPENDS
     "${CMAKE_CURRENT_SOURCE_DIR}/generated/<serial>_full*.c")
```

and pass `${GAME_GENERATED_FULL}` to `GAME_GENERATED_FULL_C` as before (it
is now a multi-value argument). No other change is required. See
`TombaRecomp/CMakeLists.txt` for a worked example.

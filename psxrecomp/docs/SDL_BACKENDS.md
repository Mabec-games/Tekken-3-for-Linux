# SDL backends

PSXRecomp uses SDL3 by default. A compatible system SDL3 package is preferred;
otherwise CMake downloads the integrity-pinned SDL 3.4.10 release. To build the
compatibility backend explicitly:

```sh
cmake -S . -B build-sdl2 -DPSX_SDL_BACKEND=SDL2
```

`PSX_SDL_BACKEND` accepts only `SDL3` or `SDL2`; it never silently changes the
requested backend. `PSX_SDL3_FETCH=OFF` makes an SDL3 build system-package-only.

## Initial Windows A/B exercise

These measurements are smoke-level comparisons, not claims that one SDL
generation makes emulation faster. Both builds used MinGW GCC 15.2, Release,
static SDL, OpenBIOS, the OpenGL renderer, and a 165 Hz Windows host. Each row is
three warmed runs of the runtime's frame-window diagnostic:

| Game and workload | SDL3 wall time | SDL2 wall time | SDL3 difference |
|---|---:|---:|---:|
| Tomba 2, frames 60–660 | 9506.5 ± 10.9 ms | 9511.3 ± 19.0 ms | -0.05% |
| Mega Man X6, frames 60–660 | 8174.0 ± 114.0 ms | 8199.2 ± 287.0 ms | -0.31% |

Every Tomba 2 run executed exactly 928,243 dirty instructions and 309,407 dirty
dispatches. Every Mega Man X6 run executed 3,962,702 dirty instructions and
1,048,509 dirty dispatches. The paced wall-time differences are smaller than
the observed variance, so the useful result is parity rather than a speed win.

The SDL3 build was additionally exercised through:

- the shared recomp-ui launcher event loop;
- the SDL renderer presentation path (Tomba 2, 240 frames); and
- the Vulkan renderer on an RTX 3080 Ti, including SDL3 instance-extension and
  surface creation APIs (Tomba 2, 240 frames).

The repeatable diagnostic setup is:

```sh
PSX_RUNTIME_PERF_DIAG=1 \
PSX_BENCH_WINDOW=60:660 \
PSX_DEV_INPUT=0 \
./game-runtime --no-launcher --disc /path/to/game.cue --renderer opengl
```

Compare only runs with identical frame windows and dirty instruction/dispatch
counts. Warm each executable and disc image before collecting results; cold
filesystem and overlay-capture state caused much larger swings than the SDL
backend in the initial exercise.

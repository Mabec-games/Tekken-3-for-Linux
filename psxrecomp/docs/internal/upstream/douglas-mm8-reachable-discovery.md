# Douglas MM8: reachable main-EXE discovery

Evaluated and adapted on 2026-07-13.

## Provenance

The opt-in reachable main-executable discovery and `game.text_size` analysis
bound were rebuilt from douglasjv's
[Mega Man 8 PSXrecomp project](https://github.com/douglasjv/mm8), specifically
commit
[`8415f3a95458c41c7f48fbe36caaf0ee82730720`](https://github.com/douglasjv/mm8/commit/8415f3a95458c41c7f48fbe36caaf0ee82730720)
(`Add reachable main executable discovery`). The implementation was adapted to
current master rather than copied verbatim: bounds are validated before
mutation, canonical page-rounded existing configs remain compatible, the EXE
entry is an explicit root, and main-image codegen retains the newer exact
static-range dispatch checks from `b39387e`.

Reachable discovery is fail-closed. It follows callable direct `jal` targets
from verified roots; an unresolved `jalr`, unseen callback, rejected seed, or
target outside the verified bound does not create a compiled entry. Such PCs
remain eligible for the runtime interpreter and overlay capture paths.

## Deliberately excluded

No MM8 addresses, identifiers, `bg2d` or other widescreen configuration,
game-specific seeds/configuration, executable patches, generated game code, or
framework pin updates were imported. All other MM8 repository and dependency
changes are outside this focused branch.

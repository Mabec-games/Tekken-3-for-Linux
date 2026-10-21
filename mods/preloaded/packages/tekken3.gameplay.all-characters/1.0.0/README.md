# All Characters Unlocked

Enabled by default for the verified Tekken 3 USA executable (SLUS-00402).
The complete playable roster is available without completing Arcade or Tekken
Force. The game's normal alternate-character selection controls still apply.

A trusted VBlank plugin adds the 21 character-availability bits at `0x80097EF0`
and raises the Doctor's progress byte at `0x80097EF6` to at least five. It runs
only after the game starts and writes only when a value needs changing, so old
saves also gain the roster. This feature does not change costume or movie flags.
There is no executable or disc patch.

The separate **Unlock Modes & Movies** feature is also enabled by default.
It raises the native Tekken Ball/Theatre menu bytes (`0x80097F26/27`) to at
least 3, adds the primary ending mask `0x001FFFFF` at `0x80097EF8`, and adds
only the three alternate ending bits `0x00010900` at `0x80097EFC`. All Tekken 3
movie entries are available, including the Tiger, Panda and Doctor variants.
Existing bits and higher progress values are retained. Settings, records,
costume flags and memory-card files are not directly edited; normal game saves
may persist the unlocks. Disabling this feature stops applying them but does
not remove unlocks already saved. Older-game movies still require their discs.

These fields were verified against the local US disc's native menu (BNS 10,
`0x800DB744`) and Theatre resolver (BNS 301, `0x801004A8`), not guessed from
adjacent save bytes. `python tools/test_modes_movies.py` exercises the actual
production callbacks and native routines offline, without booting the game.

If an old savestate was made while already on character select, leave and
re-enter that screen to refresh the game's cached roster.

Disable **Unlock All Characters** in Mods to stop applying the unlocks. Any
unlocks subsequently saved by the game remain earned in that save.

Address reference: [Thunder2's SLUS-00402 research on GameHacking.org](https://gamehacking.org/game/89985?hacker=Thunder2).
The character feature uses only the character mask and Doctor progress from
those codes; the modes/movie feature uses the local executable research above.

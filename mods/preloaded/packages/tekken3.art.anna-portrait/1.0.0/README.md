# Anna Portrait Art

This optional package replaces Anna's large character-select illustration and
loading-screen portrait with the supplied 1:2 illustration. It leaves her
small roster/team icon and costumes unchanged. Disable the feature in the
launcher and restart to restore the stock portrait.
This bonus portrait is off by default for new profiles; enable it in the
launcher if you want the illustration.

The runtime reads `mods/anna-portrait/portrait.tim` only when this package is
enabled. The source image and preview are staged alongside it. The original
disc is never modified. Regenerate the TIM after replacing the source PNG:

```powershell
python tools/anna_portrait_pack.py --source mods/assets/anna-portrait/portrait-source.png
```

The native large-portrait slot is 126×252 pixels and uses four independent
64-color palette bands. This preserves the illustration's full 1:2 composition
but does not retain its original 887×1774 resolution in-game.

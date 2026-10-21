"""Offline labeled contact sheet of the shipped Jun costume textures."""
from pathlib import Path
from PIL import Image, ImageDraw
from tim_tool import scan_tims, decode_rgba

ROOT = Path(__file__).resolve().parents[1]
sheet = Image.new('RGB', (1600, 600), '#303030')
draw = ImageDraw.Draw(sheet)
for outfit in (1, 2, 3):
    data = (ROOT/f'build-release/mods/jun/Jun-TTT1-arcade-P{outfit}.tim').read_bytes()
    draw.text((4, (outfit-1)*200+4), f'Jun outfit {outfit} / model {51+outfit}', fill='white')
    for i, tim in enumerate(scan_tims(data)):
        tile = Image.frombytes('RGBA', (tim.pixel_width, tim.image.height), decode_rgba(data,tim))
        tile.thumbnail((90,150), Image.Resampling.NEAREST)
        sheet.paste(tile, (i*100, (outfit-1)*200+24), tile)
out = ROOT/'workspace/selector-carousel-qa/jun-costume-textures.png'
sheet.save(out)
print(out)

"""Losslessly crop user screenshots; never synthesize, retouch or upscale art.

Coordinates are hand-reviewed full-body 2:3 apertures, excluding the HUD,
letterbox bars and opponent. The runtime samples the native-resolution crops.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-directory', type=Path, required=True)
    ap.add_argument('--output-directory', type=Path, required=True)
    args = ap.parse_args()
    spec = json.loads((ROOT/'tools/data/outfit_screenshot_crops.json').read_text())
    catalog = {}
    for line in (ROOT/'mods/assets/outfit-menu/catalog.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            ident, cid, label, confirm, skin, art = line.split('|')
            catalog[art] = dict(id=ident, character=int(cid), label=label,
                                confirm=confirm, skin=int(skin))
    assert len(spec['portraits']) == len(catalog)
    assert {p['art'] for p in spec['portraits']} == set(catalog)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (5*200, ((len(spec['portraits'])+4)//5)*328), '#202020')
    draw = ImageDraw.Draw(sheet)
    audit = []
    for i, row in enumerate(spec['portraits']):
        art = row['art']
        assert row['character'] == catalog[art]['character']
        source = args.source_directory/spec['sources'][row['source']-1]
        x0, y0, x1, y1 = row['box']
        with Image.open(source) as image:
            assert 0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height
            assert (x1-x0)*3 == (y1-y0)*2, art
            crop = image.convert('RGBA').crop(row['box'])
            source_size = image.size
        crop.save(args.output_directory/f'{art}.png')
        packed = b'HDRGBA01'+struct.pack('<II', *crop.size)+crop.tobytes()
        (args.output_directory/f'{art}.rgba').write_bytes(packed)
        # Verify PNG and runtime payload preserve the exact cropped source pixels.
        with Image.open(args.output_directory/f'{art}.png') as check:
            assert check.tobytes() == crop.tobytes()
        assert packed[16:] == crop.tobytes()
        tile = crop.convert('RGB').resize((192,288), Image.Resampling.LANCZOS)
        px, py = (i%5)*200, (i//5)*328
        sheet.paste(tile, (px+4,py))
        draw.text((px+4,py+292), art, fill='white')
        draw.text((px+4,py+308), f"#{row['source']} {row['side']} / {crop.width}x{crop.height}", fill='#bbbbbb')
        audit.append(dict(row | catalog[art], source_name=source.name,
                          source_size=source_size, crop_size=crop.size,
                          source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          rgba_sha256=hashlib.sha256(packed).hexdigest()))
        print(art, catalog[art]['label'], crop.size)
    sheet.save(args.output_directory/'contact-sheet.jpg', quality=95)
    (args.output_directory/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(f"PASS: {len(spec['portraits'])} unique catalog mappings; exact 2:3 crops; lossless native pixels")


if __name__ == '__main__':
    main()

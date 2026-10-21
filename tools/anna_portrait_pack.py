#!/usr/bin/env python3
"""Convert the supplied 1:2 Anna illustration into the native banded portrait TIM."""
import argparse
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_jun_ui import ps1_tim


def build(source: Path, output: Path) -> None:
    with Image.open(source) as opened:
        artwork = opened.convert('RGBA')
    w, h = artwork.size
    if not (w > 0 and h > 0 and abs(w / h - 0.5) < 0.01):
        raise ValueError('Anna illustration must be approximately 1:2; refusing to crop it')
    # Only the black background connected to the outside becomes transparent.
    # Dark regions inside her hair, gown and glove remain part of the artwork.
    ImageDraw.floodfill(artwork, (0, 0), (0, 0, 0, 0), thresh=25)
    preview = artwork.resize((126, 252), Image.Resampling.LANCZOS)
    output.mkdir(parents=True, exist_ok=True)
    preview.save(output / 'portrait-preview.png')
    (output / 'portrait.tim').write_bytes(ps1_tim(preview, True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('mods/assets/anna-portrait'))
    args = parser.parse_args()
    build(args.source, args.output)

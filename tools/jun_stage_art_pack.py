"""Compile Jun's clear host backdrop and native PS1 still-water floor assets.

This is an art preparation tool, NOT a stage installer or native TIM/VRAM pack.
Pillow and NumPy are required. Original generation sources are never modified.
"""
from pathlib import Path
import json
import struct
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'mods/assets/jun-heavenly-garden'


def periodic_edges(rgb, axes, width):
    """Match opposing sampling boundaries in a narrow, smooth texture gutter."""
    a = np.array(rgb, dtype=np.float64)
    for axis in axes:
        b = np.swapaxes(a, axis, 0)
        target = (b[0].copy() + b[-1].copy()) / 2
        first, last = b[0].copy(), b[-1].copy()
        for i in range(width):
            t = 1 - i / width
            weight = t*t*(3-2*t)
            b[i] += (target-first)*weight
            b[-1-i] += (target-last)*weight
    return Image.fromarray(np.clip(np.rint(a), 0, 255).astype('uint8'))


def palette_ps1(rgb, colors):
    # Palette RGB555 precision, as used by PS1 CLUTs. Global backdrop palette
    # is a convenient authoring format; native tiles still need their own CLUTs.
    out = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                       dither=Image.Dither.NONE)
    pal = np.array(out.getpalette(), dtype=np.uint16)
    pal = ((pal >> 3) * 255 + 15) // 31
    out.putpalette(pal.astype('uint8').tolist())
    return out


def save_payload(name, image):
    image.save(ASSETS / f'{name}.png', optimize=True)
    rgba = image.convert('RGBA')
    (ASSETS / f'{name}.rgba').write_bytes(
        b'HDRGBA01' + struct.pack('<II', *rgba.size) + rgba.tobytes())


def main():
    source = Image.open(ASSETS / 'source/background-clear-v2.png').convert('RGB')
    assert source.size == (2172, 724), 'Review crop if the authored source changes'
    # Exclude the generated letterbox AND its dark/bright antialias fringe.
    # Including those rows produces a dark roof line and a false floor seam.
    crop = (0, 215, source.width, 546)
    # Keep the generated panoramic proportions rather than squash to the
    # forest's 4:1 aspect. The stage mapping must respect this art's new framing.
    # Keep all authored detail for the host backdrop. The native builder still
    # supplies a small, VRAM-safe fallback; no enlargement invents new detail.
    background = source.crop(crop)
    # Host detail must not be flattened back into a 256-colour mosaic. Native
    # palette/VRAM budgets are enforced separately by build_jun_stage.py.
    background = periodic_edges(background, (1,), 24)
    floor = Image.open(ASSETS / 'source/ground-water-v3.png').convert('RGB')
    floor = floor.resize((64, 64), Image.Resampling.BOX)
    floor = palette_ps1(periodic_edges(floor, (1, 0), 6), 16)
    save_payload('background', background)
    save_payload('ground', floor)

    # Side-by-side copies expose wrapping seams; floor preview uses nearest
    # sampling so inspection does not hide its actual texel resolution.
    tiled = Image.new('RGB', (192, 192))
    for y in range(3):
        for x in range(3):
            tiled.paste(floor.convert('RGB'), (x*64, y*64))
    tiled.resize((768, 768), Image.Resampling.NEAREST).save(ASSETS / 'ground-repeat-preview.png')
    a = np.array(background.convert('RGB'))
    seam = np.concatenate((a[:, -192:], a[:, :192]), axis=1)
    Image.fromarray(seam).resize((768, 448), Image.Resampling.NEAREST).save(ASSETS / 'background-wrap-preview.png')

    report = {'status': 'authoring-assets; native integration in native/manifest.json', 'source_crop': crop,
              'native_palette_channel_bits': 5, 'runtime_mapping': 'native/manifest.json', 'assets': {}}
    for name, im, axes in [('background', background, (1,)), ('ground', floor, (0, 1))]:
        a = np.array(im.convert('RGB'))
        for axis in axes:
            assert np.array_equal(np.take(a, 0, axis), np.take(a, -1, axis)), name
        used = len(im.getcolors(im.width * im.height))
        if name == 'ground':
            assert used <= 16
        data = (ASSETS / f'{name}.rgba').read_bytes()
        assert data[:8] == b'HDRGBA01'
        assert struct.unpack_from('<II', data, 8) == im.size
        assert len(data) == 16 + im.width * im.height * 4
        report['assets'][name] = {'size': im.size, 'colors_used': used,
                                  'matching_edge_axes': list(axes)}
    # Validate the actual native floor palette against the water at the join,
    # rather than selecting a colour from the sky or assuming a green pool.
    water = np.array(background)[-4:].mean(axis=(0, 1))
    ground = np.array(floor.convert('RGB')).mean(axis=(0, 1))
    delta = abs(water-ground)
    assert delta.max() < 12, ('Floor/backdrop colour mismatch', water, ground)
    report['floor_join'] = {'background_water_rgb': water.tolist(),
                            'native_floor_rgb': ground.tolist(),
                            'maximum_channel_delta': float(delta.max())}
    (ASSETS / 'art-report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

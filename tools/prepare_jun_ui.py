#!/usr/bin/env python3
"""Recover Jun's five unused T3 arcade UI images from a verified local bank.

The private output includes unchanged source TIMs and PS1-format conversions.
No ROM data is embedded in the runtime or this tool.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
from PIL import Image
import tim_tool
import bns_tool

BANK_SHA = '1b148d4e7d766894431584bf191e4a3a63540a461071777e6c31c058c07347ae'
SOURCES = [
    ('portrait', 0x11b2064, 168, 252, 'ae1f58b29c30d6b8ed6baaac7c5c13ce9ad9b3d74d42207f55f88b73ee9081db'),
    ('selector-tall', 0x10f852c, 44, 68, 'c55e8ab6928b9b549f26a172f71dace0758943b9bddd8f4b60f6f9d68173548b'),
    ('selector', 0x1107140, 44, 58, '0914af495dd9c68a85df984ba16f7ad1e2a0ce7fc9c0929d90151a8912e66753'),
    ('loading-tall', 0x11133cc, 44, 34, 'aa81adb0a5ad5b8d982085cbeb26ee47e92480f71d91d8e6933ec99ed7cdd213'),
    ('loading', 0x111c528, 44, 29, 'b3954220f6e7ad07c38fdf313535d541b00b53dd58dfac2db830cc21b60990cd'),
]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def decompress(data, start=0):
    """Bounded translation of the game's 80031BFC LZ decoder."""
    out = bytearray()
    pos = start
    while True:
        if pos >= len(data):
            raise ValueError('Missing terminator')
        flags = data[pos]
        pos += 1
        if not flags:
            return bytes(out), pos - start
        while flags >= 2:
            if flags & 1:
                if pos >= len(data):
                    raise ValueError('Truncated literal')
                out.append(data[pos])
                pos += 1
            else:
                if pos + 2 > len(data):
                    raise ValueError('Truncated reference')
                ref = int.from_bytes(data[pos:pos + 2], 'big')
                pos += 2
                distance, length = (ref & 2047) or 2048, (ref >> 11) or 32
                if distance > len(out):
                    raise ValueError('Invalid distance')
                for _ in range(length):
                    out.append(out[-distance])
            if len(out) > 0x200000:
                raise ValueError('Oversized image')
            flags >>= 1

def literal_stream(data):
    out = bytearray()
    for pos in range(0, len(data), 7):
        part = data[pos:pos + 7]
        out.append((1 << (len(part) + 1)) - 1)
        out.extend(part)
    out.append(0)
    return bytes(out)

def indexed(image, colors):
    # Reserve zero for transparency. Dither is disabled to retain pixel edges.
    q = image.convert('RGB').quantize(colors=colors - 1, dither=Image.Dither.NONE)
    palette = q.getpalette()
    words = [0]
    for i in range(colors - 1):
        rgb = palette[i * 3:i * 3 + 3]
        v = sum(((c * 31 + 127) // 255) << (j * 5) for j, c in enumerate(rgb))
        words.append(v or 0x8000)
    pixels = bytes(0 if a < 128 else i + 1 for i, a in zip(q.tobytes(), image.getchannel('A').tobytes()))
    return words, pixels

def ps1_tim(image, banded=False):
    image = image.resize((126 if banded else 32, image.height), Image.Resampling.NEAREST)
    if banded:
        palette, pixels = [], bytearray()
        for y in range(0, image.height, 64):
            words, indices = indexed(image.crop((0, y, image.width, min(y + 64, image.height))), 64)
            palette.extend(words)
            pixels.extend(indices)
    else:
        palette, pixels = indexed(image, 256)
    # Destination is overridden by the native portrait uploader. Icons are
    # uploaded explicitly into the experimental roster's reserved VRAM area.
    return (struct.pack('<III4H', 16, 9, 524, 0, 480, 256, 1)
            + struct.pack('<256H', *palette)
            + struct.pack('<I4H', 12 + len(pixels), 0, 0, image.width // 2, image.height)
            + pixels)

def name_bitmap(bundle):
    """Read the second, palette-less 4bpp TIM in the native model bundle."""
    offset, length = struct.unpack_from('<II', bundle, 4)
    section = bundle[offset:offset + length]
    first_size = struct.unpack_from('<I', section, 8)[0] + 8
    magic, flags, size, x, y, words, height = struct.unpack_from('<III4H', section, first_size)
    if (magic, flags, x, y, height) != (16, 0, 80, 0, 16) or size != 12 + words * height * 2:
        raise ValueError('Unexpected native name bitmap layout')
    pixels = section[first_size + 20:first_size + 8 + size]
    if len(pixels) != words * height * 2:
        raise ValueError('Truncated native name bitmap')
    return Image.frombytes('L', (words * 4, height), bytes(v for b in pixels for v in (b & 15, b >> 4)))

def jun_name(jin, julia):
    if jin.size != (20, 16) or julia.size != (40, 16):
        raise ValueError('Unexpected source name dimensions')
    result = Image.new('L', (24, 16))
    result.paste(jin.crop((0, 0, 7, 16)), (0, 0))
    result.paste(julia.crop((7, 0, 16, 16)), (7, 0))
    result.paste(jin.crop((12, 0, 20, 16)), (16, 0))
    pixels = result.tobytes()
    return bytes(pixels[i] | pixels[i + 1] << 4 for i in range(0, len(pixels), 2)), result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bank', type=Path, default=Path('workspace/jun-import/t3-arcade/bankedroms.bin'))
    ap.add_argument('--output', type=Path, default=Path('workspace/jun-import/jun'))
    ap.add_argument('--disc', type=Path, default=Path('disc/Tekken 3 (USA) (Track 1).bin'))
    ap.add_argument('--exe', type=Path, default=Path('disc/SLUS_004.02'))
    args = ap.parse_args()
    bank = args.bank.read_bytes()
    if sha(bank) != BANK_SHA:
        raise SystemExit('Arcade bank does not match the verified local T3 set')
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    tim_tool.VRAM_HEIGHT = 1024
    manifest = {'source_sha256': BANK_SHA, 'assets': []}
    payloads = []
    for name, offset, width, height, expected in SOURCES:
        source, used = decompress(bank, offset)
        if sha(source) != expected:
            raise ValueError(f'{name}: source hash mismatch')
        tim = tim_tool.parse_tim(source)
        assert (tim.pixel_width, tim.image.height) == (width, height)
        im = Image.frombytes('RGBA', (width, height), bytes(tim_tool.decode_rgba(source, tim)))
        (out / f'Jun-T3-{name}-source.tim').write_bytes(source)
        im.save(out / f'Jun-T3-{name}-source.png')
        converted = ps1_tim(im, name == 'portrait')
        (out / f'Jun-T3-{name}.tim').write_bytes(converted)
        payloads.append(converted)
        manifest['assets'].append(dict(name=name, bank_offset=offset, compressed_size=used,
            source_sha256=expected, ps1_sha256=sha(converted), source_size=[width, height],
            ps1_size=[126 if name == 'portrait' else 32, height]))
    pack = bytearray(struct.pack('<4I', 0x3149554a, 1, 5, 0) + bytes(5 * 8))
    for i, payload in enumerate(payloads):
        struct.pack_into('<2I', pack, 16 + i * 8, len(pack), len(payload))
        pack.extend(payload)
    struct.pack_into('<I', pack, 12, len(pack))
    (out / 'Jun-T3-ui.jui').write_bytes(pack)
    manifest['pack_sha256'] = sha(pack)
    table, _, _ = bns_tool.load_us_table(args.exe)
    with bns_tool.open_bns_source(args.disc) as archive:
        bundles = [archive.read_at(table[i].offset, table[i].size) for i in (145, 153)]
    expected_bundles = ['9f52c9299a3e00d7d12ee1801fd829928f321f742b1e606b2e73de61c92bd9a8',
                        '0d1bd2a871bf6a3b368750ab107d420f0351d1554a202f7e6bf6f99fa2034594']
    if [sha(b) for b in bundles] != expected_bundles:
        raise ValueError('PS1 font bundles do not match the verified disc')
    name, preview = jun_name(*(name_bitmap(b) for b in bundles))
    (out / 'Jun-T3-name.4bpp').write_bytes(name)
    preview.point(lambda p: p * 17).save(out / 'Jun-T3-name.png')
    manifest['name'] = dict(size=[24, 16], sha256=sha(name),
        source_entries=[145, 153], source_sha256=[sha(b) for b in bundles],
        method='Original PS1 font: J and N from JIN, U from JULIA; palette indices retained')
    (out / 'ui-report.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Recovered five verified Jun images; private PS1 UI pack: {len(pack)} bytes')

if __name__ == '__main__':
    main()

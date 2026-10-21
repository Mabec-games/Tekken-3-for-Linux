"""Inspect an archived snapshot's native menu records and font palettes (no boot)."""
import struct
import sys
import zlib
from pathlib import Path

data = Path(sys.argv[1]).read_bytes()
sections = {}
offset = 36
for _ in range(struct.unpack_from('<I', data, 28)[0]):
    tag, flags, length = struct.unpack_from('<IIQ', data, offset)
    offset += 16
    payload = data[offset:offset + length]
    offset += length
    sections[tag] = zlib.decompress(payload[4:]) if flags & 1 else payload
ram = sections[2]
def string(address):
    start = address & 0x1fffff
    return ram[start:start+80].split(b'\0')[0]
print('prefix', string(0x80097d08))
print('font descriptors', ram[0x21d64:0x21d84].hex())
for i in range(10):
    p = 0xb8e44 + i*8
    pointer = struct.unpack_from('<I', ram, p)[0]
    print(i, ram[p:p+8].hex(), string(pointer))
print('working state', ram[0xebfb8:0xec028].hex())
vram = sections[8]
base = ram[0x21d64+16+14]  # Main menu uses font 1.
for style in range(16):
    index = base + style
    x = 256 + (index & 15)*16
    y = 480 + ((24 + (index >> 4)) & 31)
    colors = struct.unpack_from('<16H', vram, (y*1024+x)*2)
    print('style', style, 'CLUT', x, y, 'RGB5', [(c&31,(c>>5)&31,(c>>10)&31) for c in colors])

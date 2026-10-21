"""Offline production unlock, native menu and Theatre checks; no game/save boot."""
import struct
import subprocess
import tomllib
from test_jun_cpu import Machine, ROOT
from bns_tool import load_us_table, open_bns_source
from unicorn.mips_const import UC_MIPS_REG_S1, UC_MIPS_REG_S6


def main():
    out = ROOT / 'build-release/modes-movies-check'
    out.mkdir(exist_ok=True)
    binary = out / 'unlock-test.exe'
    flags = out / 'progress.bin'
    subprocess.run([
        str(ROOT.parent / '.tools/toolchain-v1.0.10/bin/clang.exe'),
        '-std=c11', '-O2', '-I'+str(ROOT/'psxrecomp/runtime/include'),
        str(ROOT/'tools/tests/test_unlock_characters_mod.c'),
        str(ROOT/'src/tekken3_unlock_characters_mod.c'), '-o', str(binary)
    ], check=True)
    subprocess.run([str(binary), str(flags)], check=True)
    progress = flags.read_bytes()
    manifest = tomllib.loads((ROOT/'mods/preloaded/packages/tekken3.gameplay.all-characters/1.0.0/manifest.toml').read_text())
    assert next(f for f in manifest['feature'] if f['id'] == 'modes-movies')['default_enabled']
    assert any(p['id'] == 'tekken3.unlock-modes-movies' and p['feature'] == 'modes-movies'
               for p in manifest['plugin'])

    # Execute the native menu filtering loop with fresh and unlocked progress.
    table, *_ = load_us_table(ROOT/'disc/SLUS_004.02')
    with open_bns_source(ROOT/'disc/Tekken 3 (USA) (Track 1).bin') as source:
        data = source.read_at(table[10].offset, table[10].size)
    ram = bytearray(0x800000)
    ram[0xb8d58:0xb8d58+len(data)] = data
    assert struct.unpack_from('<I', ram, 0xdb7a4)[0] == 0x91620036
    assert struct.unpack_from('<I', ram, 0xdb7b0)[0] == 0x91620037
    for unlocked in (False, True):
        m = Machine(ram)
        m.write(0x80097ef0, progress if unlocked else bytes(64))
        m.u.reg_write(UC_MIPS_REG_S1, 0x80097ef0)
        m.u.reg_write(UC_MIPS_REG_S6, 0x801e0000)
        m.call(0x800db744, end=0x800db7e8)
        # Loop packs accepted rows consecutively; unused tail is zero.
        modes = [m.read(0x801e0014+i*8, 1)[0] for i in range(10)]
        assert (7 in modes) == unlocked, modes
        assert (10 in modes) == unlocked, modes
    print('PASS: native main menu exposes Ball and Theatre with production flags')

    with open_bns_source(ROOT/'disc/Tekken 3 (USA) (Track 1).bin') as source:
        data = source.read_at(table[301].offset, table[301].size)
    ram = bytearray(0x800000)
    ram[0xb8d58:0xb8d58+len(data)] = data
    m = Machine(ram)
    m.write(0x80097ef0, progress)
    movies = 0
    for row in range(26):
        address = 0x800ba160 + row*28
        first, alternate, _, mask, kind = struct.unpack('<hhIII', m.read(address, 16))
        expected = alternate if kind in (1, 2) else first
        actual = m.call(0x801004a8, address)
        assert actual == expected & 0xffffffff, (row, actual, expected)
        if first < 0:  # Native blank slots must remain blank.
            continue
        movies += 1
        if mask:
            m.write(0x80097ef8, bytes(8))
            assert m.call(0x801004a8, address) == 0xffffffff
            m.write(0x80097ef0, progress)
        if kind in (1, 2):
            # Native Kuma/Doctor rows also support their primary ending.
            m.w(0x80097efc, 0)
            assert m.call(0x801004a8, address) == first
            m.write(0x80097ef0, progress)
    assert movies == 22
    print('PASS: all 22 native movie entries plus alternate variants; blank slots preserved')


if __name__ == '__main__':
    main()

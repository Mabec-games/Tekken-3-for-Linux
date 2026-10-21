#!/usr/bin/env python3
"""Reproduce the opt-in Jun renderer probe from the verified local arcade dump.

The generated renderer and game data stay in ignored workspace/. This tool
does not modify the PS1 disc, executable, or normal build configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BANK_SHA = "e06862305a58a1f9b98c356899c298b429477f0d6d12e0cd8ddb0129194e10ef"
RAM_SHA = "3bc079e7defefa63825474867165a803e348dad138cc6b3a9f13f0d5818ad3bb"
MODEL_SHA = "c436fbe39bbc98acf24e72a9919812253e95f948ce7a0cd500f9d3f50ef10ddc"
TEXTURE_SHA = "72aadb81c2cfd43368185180d408ebde13a9f0d8b0456a35279c957919179877"
RELOCATION_SHA = "d7590230c1176e07dc5d5f784722cc0c9b8b8fb8ebe5b2c415338b270a6ccd7b"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verified(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    if sha(data) != expected:
        # Frame timers and scratch RAM differ across fresh emulator runs.
        # Verify every byte consumed by this version of the import pipeline.
        # Final runtime pack hashes are checked again by import_jun.py.
        reference = ROOT / 'tools/data/jun_capture_ranges.json'
        ranges = json.loads(reference.read_text()).get(path.name, []) if reference.is_file() else []
        if (len(data) != 0x400000 or not path.name.endswith('-ram.bin') or not ranges
            or any(sha(data[r['offset']:r['offset'] + r['size']]) != r['sha256'] for r in ranges)):
            raise ValueError(f"Unexpected SHA-256 for {path}")
    return data


def model_relocations(model: bytes, live: bytes, base: int) -> list[int]:
    """Accept only a complete word-for-word match, allowing additive pointers."""
    if len(model) != len(live) or len(model) % 4:
        raise ValueError("Model and live capture must have equal aligned sizes")
    offsets = []
    for p in range(0, len(model), 4):
        original, observed = struct.unpack_from("<I", model, p)[0], struct.unpack_from("<I", live, p)[0]
        if original == observed:
            continue
        if not 0 < original < len(model) or observed != base + original:
            raise ValueError(f"Unexplained live model change at 0x{p:x}")
        offsets.append(p)
    return offsets


def check_textures(data: bytes) -> list[dict]:
    """Validate concatenated TIMs and the two-page packing used by the probe."""
    p = 0
    tiles = []
    while p < len(data):
        if data[p:] == b"\0\0\0\0":
            break  # Arcade bank terminator, outside the individual TIMs.
        if p + 8 > len(data):
            raise ValueError("Truncated TIM header")
        magic, flags = struct.unpack_from("<II", data, p)
        if magic != 16 or flags not in (8, 9):
            raise ValueError("Only original indexed TIMs are accepted")
        start = p
        p += 8
        for palette in (True, False):
            if p + 12 > len(data):
                raise ValueError("Truncated TIM block")
            size, x, y, width, height = struct.unpack_from("<I4H", data, p)
            if not width or not height or size != 12 + width * height * 2 or p + size > len(data):
                raise ValueError("Invalid TIM block dimensions")
            if palette:
                if x + width > 256 or y + height > 2:
                    raise ValueError("CLUT exceeds the reserved Jun palette rows")
            else:
                if x // 64 != (x + width - 1) // 64 or x + width > 128 or y + height > 128:
                    raise ValueError("Texture tile cannot fit the PS1 costume allocation")
                tiles.append(dict(offset=start, mode=flags & 3, x=x, y=y, width=width, height=height))
            p += size
    return tiles


def export_costumes(bank: bytes, out: Path) -> list[dict]:
    """Export exact ARC members; relocation maps were checked against MAME.

    The arcade lookup at 800111FC names models 46, 47 and 118. Model 118
    uses member 16 of the expansion archive (its model IDs start at 102).
    No guessed signature boundaries or recolored substitute meshes are used.
    """
    manifest = json.loads((ROOT / 'tools/data/jun_costumes.json').read_text())
    if sha(bank) != manifest['bank_sha256']:
        raise ValueError('Unexpected costume source bank')
    exports = []
    for spec in manifest['costumes']:
        model = bank[spec['model_offset']:spec['model_offset'] + spec['model_size']]
        texture = bank[spec['texture_offset']:spec['texture_offset'] + spec['texture_size']]
        offsets = spec['relocations']
        relocations = struct.pack(f'<{len(offsets)}I', *offsets)
        if (sha(model) != spec['model_sha256'] or sha(texture) != spec['texture_sha256']
                or sha(relocations) != spec['relocation_sha256']):
            raise ValueError(f"Jun outfit {spec['outfit']} archive members changed")
        if (struct.unpack_from('<I', model)[0] != 30 or offsets != sorted(set(offsets))
                or any(p % 4 or p > len(model)-4 or not 0 < struct.unpack_from('<I', model, p)[0] < len(model)
                       for p in offsets)):
            raise ValueError('Invalid costume relocation map')
        tiles = check_textures(texture)
        if len(tiles) != spec['texture_tiles']:
            raise ValueError('Incomplete costume texture bank')
        out.mkdir(parents=True, exist_ok=True)
        for suffix, data in (('3dm', model), ('tim', texture), ('relocs', relocations)):
            (out / f"Jun-TTT1-arcade-P{spec['outfit']}.{suffix}").write_bytes(data)
        exports.append(dict(outfit=spec['outfit'], arcade_model=spec['arcade_model'],
                            model_sha256=sha(model), texture_sha256=sha(texture),
                            relocation_count=len(offsets), texture_tiles=len(tiles)))
    return exports


def prepare(work: Path, recompiler: Path) -> dict:
    bank = verified(work / "ttt1/bankedroms.bin", BANK_SHA)
    ram = verified(work / "jun-select-ram.bin", RAM_SHA)
    model = bank[0x16C64AC:0x16C64AC + 44732]
    textures = bank[0x1295D44:0x1295D44 + 39492]
    if sha(model) != MODEL_SHA or sha(textures) != TEXTURE_SHA:
        raise ValueError("Jun archive members do not match the verified exports")
    offsets = model_relocations(model, ram[0x354108:0x354108 + len(model)], 0x80354108)
    relocations = struct.pack(f"<{len(offsets)}I", *offsets)
    if sha(relocations) != RELOCATION_SHA:
        raise ValueError("Jun's relocation map changed")
    tiles = check_textures(textures)
    if len(tiles) != 26:
        raise ValueError("Expected all 26 Jun texture tiles")

    code_start, code_end = 0x10DC94, 0x10E8E8
    code = bytearray(ram[code_start:code_end])
    # Relocate the donor's depth, position and lighting scratch buffers to
    # the corresponding SLUS-00402 buffers. Internal branches stay intact.
    patches = {
        0x8010DCB8: 0x3C12800A, 0x8010DCBC: 0x2652CD4E,
        0x8010DCC0: 0x3C13800A, 0x8010DCC4: 0x2673BD4C,
        0x8010E240: 0x3C12800A, 0x8010E244: 0x2652D550,
        0x8010E2C8: 0x3C0E800B, 0x8010E2CC: 0x8DCEDE1C,
    }
    for address, replacement in patches.items():
        struct.pack_into("<I", code, address - 0x80000000 - code_start, replacement)
    header = bytearray(2048)
    header[:8] = b"PS-X EXE"
    struct.pack_into("<I", header, 0x10, 0x80000000 + code_start)
    struct.pack_into("<II", header, 0x18, 0x80000000 + code_start, len(code))
    struct.pack_into("<I", header, 0x30, 0x801FFFF0)

    if not recompiler.is_file():
        raise ValueError(f"Build the recompiler first: {recompiler}")
    out = work / "jun"
    out.mkdir(parents=True, exist_ok=True)
    costumes = export_costumes(bank, out)
    executable = work / "jun-render.exe"
    executable.write_bytes(header + code)
    seeds = work / "jun-render-seeds.txt"
    seeds.write_text("0x8010DC94\n")
    subprocess.run([str(recompiler), str(executable), "--seeds", str(seeds),
                    "--out-dir", str(work / "generated"), "--strict"], check=True)
    report = dict(schema_version=1, model_sha256=MODEL_SHA, texture_sha256=TEXTURE_SHA,
                  relocation_sha256=RELOCATION_SHA, relocation_count=len(offsets),
                  texture_tiles=tiles, costumes=costumes, renderer_patches={hex(k): hex(v) for k, v in patches.items()},
                  status="Jun model, textures and renderer prepared; run the motion, combat, UI and voice converters next")
    (work / "prepare-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "workspace/jun-import")
    parser.add_argument("--recompiler", type=Path, default=ROOT / "build-recompiler/psxrecomp-game.exe")
    args = parser.parse_args()
    report = prepare(args.work_dir.resolve(), args.recompiler.resolve())
    print(f"Prepared {report['relocation_count']} relocations and {len(report['texture_tiles'])} textures")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Audit dormant Tekken 3 character records in Tekken 5 Arcade History.

The probe is intentionally read-only.  It correlates the PS2 port's character
descriptor table and nested ``romdata.arc`` members with a verified local
System 12 Tekken 3 bank.  Retail-derived inputs and outputs belong under the
ignored ``workspace/`` directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import tim_tool
from tekken5_arcade_history import (
    ProbeError,
    decompress_arcade_executable,
    parse_linear_archive,
)


DESCRIPTOR_OFFSETS = {
    "PAUL": 0x2E2FB0,
    "LAW": 0x2E2FC0,
    "LEI": 0x2E2FD0,
    "KING": 0x2E2FE0,
    "YOSHIMITSU": 0x2E3000,
    "NINA": 0x2E3010,
    "ANNA": 0x2E3020,
    "HWOARANG": 0x2E3040,
    "XIAOYU": 0x2E3050,
    "XIAOYU_ALT": 0x2E3060,
    "EDDY": 0x2E3070,
    "TIGER": 0x2E3080,
    "JIN": 0x2E3090,
    "JIN_ALT": 0x2E30A0,
    "JULIA": 0x2E30B0,
    "KUMA": 0x2E30C0,
    "PANDA": 0x2E30D0,
    "BRYAN": 0x2E30E0,
    "HEIHACHI": 0x2E3100,
    "OGRE": 0x2E3110,
    "MOKUJIN": 0x2E3120,
    "GUN_JACK": 0x2E3140,
    "TRUE_OGRE": 0x2E3150,
    "JUN": 0x2E3160,
    "SAKE": 0x2E3170,
}
LOOKUP_FILE_OFFSET = 0x108FB8
LOAD_SEGMENT_DELTA = 0xFF000


@dataclass(frozen=True)
class CompactSlice:
    index: int
    offset: int
    size: int


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_compact_archive(data: bytes) -> list[CompactSlice]:
    """Parse the compact final-member variant used by model bundles.

    It has a count, initial offset, ``size/end`` pairs for all non-final
    members, and a final size whose end is implicit.  Alignment bytes may
    follow the final member.
    """
    if len(data) < 12:
        raise ProbeError("compact archive is shorter than its header")
    count, first = struct.unpack_from("<II", data)
    header_size = 4 + count * 8
    if not 0 < count < 1000 or first != header_size:
        raise ProbeError("not a compact archive")
    result: list[CompactSlice] = []
    offset = first
    for index in range(count):
        size = struct.unpack_from("<I", data, 8 + index * 8)[0]
        if offset + size > len(data):
            raise ProbeError(f"compact member {index} extends outside input")
        result.append(CompactSlice(index, offset, size))
        if index + 1 < count:
            end = struct.unpack_from("<I", data, 12 + index * 8)[0]
            if offset + size != end:
                raise ProbeError(f"compact member {index} has a non-canonical end")
            offset = end
    return result


def descriptor(elf: bytes, name: str) -> dict[str, object]:
    offset = DESCRIPTOR_OFFSETS[name]
    raw = elf[offset : offset + 16]
    if len(raw) != 16:
        raise ProbeError(f"truncated descriptor {name}")
    name_pointer = struct.unpack_from("<I", raw)[0]
    return {
        "name": name,
        "file_offset": offset,
        "name_pointer": name_pointer,
        "fields": list(raw[4:12]),
        "tail_u32": struct.unpack_from("<I", raw, 12)[0],
        "raw": raw.hex(),
    }


def nested_member(container: bytes, index: int) -> bytes:
    members = parse_linear_archive(container)
    member = members[index]
    return container[member.offset : member.offset + member.size]


def exact_member_matches(
    ps2_romdata_dir: Path, arcade_bank: bytes, ui_report: dict[str, object]
) -> list[dict[str, object]]:
    sources = ui_report.get("assets")
    if not isinstance(sources, list):
        raise ProbeError("UI report has no asset list")
    containers = []
    for path in sorted(ps2_romdata_dir.glob("entry-*.bin")):
        data = path.read_bytes()
        try:
            members = parse_linear_archive(data)
        except ProbeError:
            continue
        containers.append((path, data, members))

    matches = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        offset = int(item["bank_offset"])
        size = int(item["compressed_size"])
        source = arcade_bank[offset : offset + size]
        for path, data, members in containers:
            found = data.find(source)
            if found < 0:
                continue
            owner = next(
                (member for member in members if member.offset <= found < member.end),
                None,
            )
            matches.append(
                {
                    "asset": item["name"],
                    "source_offset": offset,
                    "compressed_size": size,
                    "container": path.name,
                    "container_offset": found,
                    "member_index": None if owner is None else owner.index,
                    "member_size": None if owner is None else owner.size,
                    "exact_compressed_bytes": True,
                }
            )
    return matches


def model_comparison(model_container: bytes, indices: list[int]) -> dict[str, object]:
    outer = parse_linear_archive(model_container)
    all_parts: dict[str, list[tuple[int, int]]] = {}
    reports = {}
    for member in outer:
        contents = model_container[member.offset : member.offset + member.size]
        try:
            parts = parse_compact_archive(contents)
        except ProbeError:
            continue
        rows = []
        for part in parts:
            payload = contents[part.offset : part.offset + part.size]
            digest = sha256(payload)
            all_parts.setdefault(digest, []).append((member.index, part.index))
            rows.append(
                {
                    "index": part.index,
                    "size": part.size,
                    "sha256": digest,
                }
            )
        if member.index in indices:
            reports[str(member.index)] = {
                "size": member.size,
                "sha256": sha256(contents),
                "parts": rows,
            }
    for member_index, report in reports.items():
        for part in report["parts"]:
            part["exact_matches"] = [
                {"member": member, "part": subpart}
                for member, subpart in all_parts[part["sha256"]]
                if member != int(member_index) or subpart != part["index"]
            ]
    return reports


def extract_dormant_assets(romdata_dir: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise ProbeError(f"output already exists: {output}")
    output.mkdir(parents=True)
    tim_tool.VRAM_HEIGHT = 1024
    report: dict[str, object] = {
        "output": str(output),
        "warning": (
            "Only entries 3, 4, and 6 have been independently identified as "
            "Jun UI by exact System 12 source matches. Equal numeric indices in "
            "other romdata groups are extracted for research, not asserted to "
            "belong to Jun or Sake."
        ),
        "indices": {},
    }
    slots = report["indices"]
    assert isinstance(slots, dict)

    for slot in (0x11, 0x15):
        slot_dir = output / f"slot-{slot:02x}"
        slot_dir.mkdir()
        written = []
        for entry_index in (0, 3, 4, 5, 6, 9):
            container_path = romdata_dir / f"entry-{entry_index:02d}.bin"
            container = container_path.read_bytes()
            members = parse_linear_archive(container)
            if slot >= len(members):
                continue
            member = members[slot]
            compressed = container[member.offset : member.offset + member.size]
            decoded = decompress_arcade_executable(compressed)
            raw_path = slot_dir / f"entry-{entry_index:02d}-decoded.bin"
            raw_path.write_bytes(decoded)
            images = tim_tool.scan_tims(decoded)
            previews = []
            for image_index, image in enumerate(images):
                png_path = slot_dir / f"entry-{entry_index:02d}-tim-{image_index:02d}.png"
                rgba = tim_tool.decode_rgba(decoded, image)
                png_path.write_bytes(
                    tim_tool.encode_png_rgba(image.pixel_width, image.image.height, rgba)
                )
                previews.append(png_path.name)
            written.append(
                {
                    "entry": entry_index,
                    "compressed_size": len(compressed),
                    "decoded_size": len(decoded),
                    "decoded_sha256": sha256(decoded),
                    "tim_count": len(images),
                    "previews": previews,
                }
            )

        model_container = (romdata_dir / "entry-11.bin").read_bytes()
        model_member = nested_member(model_container, slot)
        model_parts = []
        for part in parse_compact_archive(model_member):
            compressed = model_member[part.offset : part.offset + part.size]
            decoded = decompress_arcade_executable(compressed)
            suffix = "3dmk" if decoded[8:12] == b"3DMK" else "bin"
            part_path = slot_dir / f"entry-11-part-{part.index:02d}.{suffix}"
            part_path.write_bytes(decoded)
            images = tim_tool.scan_tims(decoded)
            previews = []
            for image_index, image in enumerate(images):
                png_path = slot_dir / (
                    f"entry-11-part-{part.index:02d}-tim-{image_index:02d}.png"
                )
                rgba = tim_tool.decode_rgba(decoded, image)
                png_path.write_bytes(
                    tim_tool.encode_png_rgba(image.pixel_width, image.image.height, rgba)
                )
                previews.append(png_path.name)
            model_parts.append(
                {
                    "part": part.index,
                    "decoded_size": len(decoded),
                    "decoded_sha256": sha256(decoded),
                    "kind": suffix,
                    "previews": previews,
                }
            )
        slots[f"0x{slot:02x}"] = {"entries": written, "model_parts": model_parts}

    (output / "manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extract",
        type=Path,
        default=Path("workspace/tekken5-arcade-history"),
        help="output directory created by tekken5_arcade_history.py",
    )
    parser.add_argument(
        "--arcade-bank",
        type=Path,
        help="optional verified System 12 bankedroms.bin for exact UI comparison",
    )
    parser.add_argument(
        "--ui-report",
        type=Path,
        help="optional ui-report.json produced by prepare_jun_ui.py",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--output",
        type=Path,
        help="fresh ignored directory for decoded dormant-slot assets and previews",
    )
    args = parser.parse_args()

    elf_path = args.extract / "executables" / "tekken3.elf"
    romdata_dir = args.extract / "tekken3" / "romdata"
    elf = elf_path.read_bytes()
    report: dict[str, object] = {
        "elf": str(elf_path),
        "elf_sha256": sha256(elf),
        "literal_kazuya_offsets": [
            index for spelling in (b"KAZUYA", b"kazuya")
            for index in range(len(elf)) if elf.startswith(spelling, index)
        ],
        "descriptors": [descriptor(elf, name) for name in DESCRIPTOR_OFFSETS],
        "audio_filename_literals": {
            name: elf.find(name.encode("ascii"))
            for name in ("jun.vb", "jun.vh", "kazuya.vb", "kazuya.vh", "gon.vb", "gon.vh")
        },
    }

    lookup = [
        struct.unpack_from("<I", elf, LOOKUP_FILE_OFFSET + index * 4)[0]
        for index in range(23 * 4)
    ]
    report["character_lookup"] = {
        "file_offset": LOOKUP_FILE_OFFSET,
        "entries": [
            {
                "character_id": character_id,
                "descriptor_pointers": lookup[character_id * 4 : character_id * 4 + 4],
            }
            for character_id in range(23)
        ],
        "jun_all_four_costumes": [
            hex(value) for value in lookup[17 * 4 : 17 * 4 + 4]
        ],
        "sake_all_four_costumes": [
            hex(value) for value in lookup[21 * 4 : 21 * 4 + 4]
        ],
    }

    models = (romdata_dir / "entry-11.bin").read_bytes()
    report["unmapped_same_index_model_members"] = model_comparison(
        models, [0x11, 0x15]
    )
    report["unmapped_same_index_warning"] = (
        "romdata entry 11 has its own model numbering. Its members 17 and 21 "
        "are not proven to be the character IDs Jun and Sake."
    )

    if bool(args.arcade_bank) != bool(args.ui_report):
        parser.error("--arcade-bank and --ui-report must be supplied together")
    if args.arcade_bank and args.ui_report:
        bank = args.arcade_bank.read_bytes()
        source_report = json.loads(args.ui_report.read_text(encoding="utf-8"))
        expected = source_report.get("source_sha256")
        if expected and sha256(bank) != expected:
            raise ProbeError("arcade bank does not match UI report source hash")
        report["exact_arcade_ui_matches"] = exact_member_matches(
            romdata_dir, bank, source_report
        )
    if args.output:
        report["extraction"] = extract_dormant_assets(romdata_dir, args.output)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Tekken 3 ELF: {report['elf_sha256']}")
        print(f"KAZUYA literal offsets: {report['literal_kazuya_offsets'] or 'none'}")
        for item in report["descriptors"][-2:]:
            print(
                f"{item['name']}: descriptor file+0x{item['file_offset']:x}, "
                f"fields={item['fields']}, raw={item['raw']}"
            )
        print(
            "character lookup 17 (Jun): "
            f"{report['character_lookup']['jun_all_four_costumes']}"
        )
        print(
            "character lookup 21 (Sake): "
            f"{report['character_lookup']['sake_all_four_costumes']}"
        )
        for name, offset in report["audio_filename_literals"].items():
            print(f"{name}: {'absent' if offset < 0 else f'file+0x{offset:x}'}")
        for index, item in report["unmapped_same_index_model_members"].items():
            print(f"unmapped model member {index}: {item['size']} bytes, {item['sha256']}")
            for part in item["parts"]:
                print(
                    f"  part {part['index']}: {part['size']} bytes; "
                    f"exact matches={part['exact_matches']}"
                )
        for item in report.get("exact_arcade_ui_matches", []):
            print(
                f"{item['asset']}: exact compressed bytes in "
                f"{item['container']} member {item['member_index']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create a reproducible visual/data census of Tekken 5's Tekken 3 port.

The input is the ignored extraction produced by ``tekken5_arcade_history.py``.
No retail data is copied into the repository: JSON and contact sheets are
written to an ignored workspace directory selected by the caller.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from PIL import Image, ImageDraw

import tim_tool
from tekken5_arcade_history import (
    ProbeError,
    decompress_arcade_executable,
    parse_linear_archive,
)
from tekken5_t3_character_probe import (
    CompactSlice,
    DESCRIPTOR_OFFSETS,
    descriptor,
    parse_compact_archive,
)


BASE_CHARACTER_NAMES = {
    0: "PAUL",
    1: "LAW",
    2: "LEI",
    3: "KING",
    4: "YOSHIMITSU",
    5: "NINA",
    6: "HWOARANG",
    7: "XIAOYU",
    8: "EDDY",
    9: "JIN",
    10: "JULIA",
    11: "KUMA",
    12: "BRYAN",
    13: "HEIHACHI",
    14: "OGRE",
    15: "MOKUJIN",
    16: "GUN JACK",
    17: "JUN (dormant)",
    18: "ANNA",
}

UI_NAMES = {
    3: BASE_CHARACTER_NAMES,
    4: BASE_CHARACTER_NAMES | {19: "TRUE OGRE"},
    5: BASE_CHARACTER_NAMES
    | {
        19: "SOUL (Tiger pre-production name)",
        20: "INSECT (orphan nameplate)",
        21: "SAKE (dormant)",
        22: "PANDA (duplicate)",
        23: "TIGER",
        24: "PANDA",
    },
    6: BASE_CHARACTER_NAMES
    | {
        19: "WHO IS IT? silhouette",
        20: "TRUE OGRE",
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decoded_members(path: Path) -> list[tuple[int, bytes, bytes]]:
    container = path.read_bytes()
    try:
        members = parse_linear_archive(container)
    except ProbeError:
        try:
            members = parse_compact_archive(container)
        except ProbeError:
            # Entry 10 is the same compact variant with up to three alignment
            # bytes between members and after the final payload.
            count, first = struct.unpack_from("<II", container)
            if not 0 < count < 1000 or first != 4 + count * 8:
                raise
            members = []
            offset = first
            for index in range(count):
                size = struct.unpack_from("<I", container, 8 + index * 8)[0]
                if offset + size > len(container):
                    raise ProbeError("padded compact member extends outside input")
                members.append(CompactSlice(index, offset, size))
                if index + 1 < count:
                    next_offset = struct.unpack_from(
                        "<I", container, 12 + index * 8
                    )[0]
                    if not offset + size <= next_offset < len(container):
                        raise ProbeError("invalid padded compact member end")
                    offset = next_offset
    result = []
    for member in members:
        raw = container[member.offset : member.offset + member.size]
        result.append((member.index, raw, decompress_arcade_executable(raw)))
    return result


def decode_tim(data: bytes) -> tuple[Image.Image, tim_tool.TimImage]:
    image = tim_tool.parse_tim(data)
    rgba = tim_tool.decode_rgba(data, image)
    return Image.frombytes(
        "RGBA", (image.pixel_width, image.image.height), bytes(rgba)
    ), image


def repair_name_tim(data: bytes) -> tuple[bytes, bool]:
    """Repair the arcade name strip's inconsistent image-size word.

    Several original streams declare the image block 16 bytes too long (and a
    few 16 bytes too short), while their width/height and decoded payload are
    internally consistent.  The game ignores that word after upload.  Adjust a
    private copy solely so the strict TIM decoder can render the bitmap.
    """
    patched = bytearray(data)
    clut_size = struct.unpack_from("<I", patched, 8)[0]
    image_offset = 8 + clut_size
    _, _, _, width_words, height = struct.unpack_from(
        "<IHHHH", patched, image_offset
    )
    expected = 12 + width_words * height * 2
    declared = struct.unpack_from("<I", patched, image_offset)[0]
    struct.pack_into("<I", patched, image_offset, expected)
    return bytes(patched), declared != expected


def contact_sheet(
    items: list[tuple[str, Image.Image]], output: Path, columns: int = 8
) -> None:
    if not items:
        return
    label_height = 24
    cell_width = max(image.width for _, image in items) + 20
    cell_height = max(image.height for _, image in items) + label_height + 16
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGBA", (cell_width * columns, cell_height * rows), "#181818")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(items):
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        checker = Image.new("RGBA", image.size, "#383838")
        sheet.alpha_composite(checker, (x + 10, y + label_height))
        sheet.alpha_composite(image, (x + 10, y + label_height))
        draw.text((x + 6, y + 5), label, fill="white")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output, quality=95)


def ui_census(romdata: Path, output: Path) -> dict[str, object]:
    report: dict[str, object] = {}
    for entry in (3, 4, 5, 6):
        names = UI_NAMES[entry]
        rendered = []
        rows = []
        for index, raw, decoded in decoded_members(romdata / f"entry-{entry:02d}.bin"):
            repaired = False
            source = decoded
            if entry == 5:
                source, repaired = repair_name_tim(source)
            image, tim = decode_tim(source)
            label = f"{index:02d} {names.get(index, 'unmapped')}"
            rendered.append((label, image.resize((image.width * 2, image.height * 2))))
            rows.append(
                {
                    "index": index,
                    "label": names.get(index, "unmapped"),
                    "compressed_size": len(raw),
                    "decoded_size": len(decoded),
                    "decoded_sha256": sha256(decoded),
                    "width": tim.pixel_width,
                    "height": tim.image.height,
                    "repaired_size_word_for_preview": repaired,
                }
            )
        contact_sheet(rendered, output / f"entry-{entry:02d}-contact.jpg", 7)
        report[f"entry-{entry:02d}"] = rows
    return report


def model_texture_census(romdata: Path, output: Path) -> dict[str, object]:
    container = (romdata / "entry-11.bin").read_bytes()
    members = parse_linear_archive(container)
    thumbnails = []
    rows = []
    for member in members:
        bundle = container[member.offset : member.offset + member.size]
        parts = parse_compact_archive(bundle)
        part_rows = []
        for part in parts:
            compressed_part = bundle[part.offset : part.offset + part.size]
            decoded_part = decompress_arcade_executable(compressed_part)
            part_rows.append(
                {
                    "part": part.index,
                    "compressed_size": len(compressed_part),
                    "decoded_size": len(decoded_part),
                    "kind": (
                        "3DMK" if decoded_part[8:12] == b"3DMK" else "texture/data"
                    ),
                    "decoded_sha256": sha256(decoded_part),
                }
            )
        first = parts[0]
        raw = bundle[first.offset : first.offset + first.size]
        decoded = decompress_arcade_executable(raw)
        images = tim_tool.scan_tims(decoded)
        decoded_images = []
        for image in images:
            rgba = tim_tool.decode_rgba(decoded, image)
            decoded_images.append(
                Image.frombytes(
                    "RGBA", (image.pixel_width, image.image.height), bytes(rgba)
                )
            )
        # A compact mosaic is enough to identify uniforms, faces, fur and props.
        mosaic = Image.new("RGBA", (192, 192), "#303030")
        x = y = row_height = 0
        for image in decoded_images:
            thumb = image.copy()
            thumb.thumbnail((64, 64), Image.Resampling.NEAREST)
            if x + thumb.width > mosaic.width:
                x = 0
                y += row_height
                row_height = 0
            if y + thumb.height > mosaic.height:
                break
            mosaic.alpha_composite(thumb, (x, y))
            x += thumb.width
            row_height = max(row_height, thumb.height)
        base = member.index // 2
        side = "P1" if member.index % 2 == 0 else "P2"
        label = f"model {member.index:02d} pair {base:02d} {side}"
        thumbnails.append((label, mosaic))
        rows.append(
            {
                "member": member.index,
                "pair": base,
                "side": side,
                "bundle_size": member.size,
                "texture_count": len(images),
                "texture_sha256": sha256(decoded),
                "parts": part_rows,
            }
        )
    contact_sheet(thumbnails, output / "entry-11-model-textures-contact.jpg", 6)
    return {
        "members": rows,
        "member_count": len(rows),
        "all_members_have_one_3dmk_part": all(
            sum(part["kind"] == "3DMK" for part in row["parts"]) == 1
            for row in rows
        ),
    }


def descriptor_stage_census(elf_path: Path) -> dict[str, object]:
    elf = elf_path.read_bytes()
    rows = []
    for name in DESCRIPTOR_OFFSETS:
        item = descriptor(elf, name)
        fields = item["fields"]
        assert isinstance(fields, list)
        rows.append(
            {
                "descriptor": name,
                "stage_id": fields[6],
                "music_or_sound_id": fields[7],
            }
        )
    return {
        "assignments": rows,
        "unique_stage_ids": sorted({row["stage_id"] for row in rows}),
        "jun_stage_id": next(row["stage_id"] for row in rows if row["descriptor"] == "JUN"),
        "sake_stage_id": next(row["stage_id"] for row in rows if row["descriptor"] == "SAKE"),
    }


def generic_tim_census(romdata: Path, output: Path) -> dict[str, object]:
    """Render the remaining small graphics groups without semantic guesses."""
    result: dict[str, object] = {}
    for entry in (0, 2, 7, 8, 10, 13, 14, 15):
        rendered = []
        rows = []
        for index, raw, decoded in decoded_members(romdata / f"entry-{entry:02d}.bin"):
            images = tim_tool.scan_tims(decoded)
            previews = []
            for tim in images:
                rgba = tim_tool.decode_rgba(decoded, tim)
                image = Image.frombytes(
                    "RGBA", (tim.pixel_width, tim.image.height), bytes(rgba)
                )
                image.thumbnail((256, 160), Image.Resampling.NEAREST)
                previews.append(image)
            if previews:
                width = max(image.width for image in previews)
                height = sum(image.height for image in previews[:6])
                mosaic = Image.new("RGBA", (width, max(1, height)), "#303030")
                y = 0
                for image in previews[:6]:
                    mosaic.alpha_composite(image, (0, y))
                    y += image.height
                rendered.append((f"member {index:02d}", mosaic))
            rows.append(
                {
                    "member": index,
                    "compressed_size": len(raw),
                    "decoded_size": len(decoded),
                    "decoded_sha256": sha256(decoded),
                    "tim_count": len(images),
                    "dimensions": [
                        [tim.pixel_width, tim.image.height] for tim in images
                    ],
                }
            )
        contact_sheet(rendered, output / f"entry-{entry:02d}-misc-contact.jpg", 4)
        result[f"entry-{entry:02d}"] = rows
    return result


def texture_pack_census(romdata: Path, output: Path) -> dict[str, object]:
    """Build a tile overview of entry 9's 39 uniform texture packs."""
    rendered = []
    rows = []
    for index, raw, decoded in decoded_members(romdata / "entry-09.bin"):
        images = tim_tool.scan_tims(decoded)
        mosaic = Image.new("RGBA", (192, 192), "#303030")
        for image_index, tim in enumerate(images[:36]):
            rgba = tim_tool.decode_rgba(decoded, tim)
            image = Image.frombytes(
                "RGBA", (tim.pixel_width, tim.image.height), bytes(rgba)
            )
            image.thumbnail((32, 32), Image.Resampling.NEAREST)
            x = (image_index % 6) * 32
            y = (image_index // 6) * 32
            mosaic.alpha_composite(image, (x, y))
        rendered.append((f"pack {index:02d}", mosaic))
        rows.append(
            {
                "member": index,
                "compressed_size": len(raw),
                "decoded_size": len(decoded),
                "texture_count": len(images),
                "decoded_sha256": sha256(decoded),
            }
        )
    contact_sheet(rendered, output / "entry-09-texture-packs-contact.jpg", 6)
    return {"members": rows}


def exact_arcade_matches(romdata: Path, bank_path: Path) -> list[dict[str, object]]:
    bank = bank_path.read_bytes()
    matches = []
    for entry in range(18):
        path = romdata / f"entry-{entry:02d}.bin"
        try:
            members = decoded_members(path)
        except (ProbeError, ValueError):
            continue
        for index, raw, _ in members:
            offset = bank.find(raw)
            if offset >= 0:
                matches.append(
                    {
                        "entry": entry,
                        "member": index,
                        "size": len(raw),
                        "arcade_bank_offset": offset,
                        "sha256": sha256(raw),
                    }
                )
    return matches


def decompress_at_bounded(
    source: bytes, start: int, maximum_output: int
) -> tuple[bytes, int] | None:
    """Try one arcade LZ stream without allowing a false hit to grow wildly."""
    output = bytearray()
    position = start
    try:
        while position < len(source):
            control = source[position]
            position += 1
            if control == 0:
                return bytes(output), position - start
            if control < 2:
                continue
            while control >= 2:
                if control & 1:
                    output.append(source[position])
                    position += 1
                else:
                    token = (source[position] << 8) | source[position + 1]
                    position += 2
                    distance = token & 0x7FF or 0x800
                    length = token >> 11 or 0x20
                    if distance > len(output):
                        return None
                    for _ in range(length):
                        output.append(output[-distance])
                if len(output) > maximum_output:
                    return None
                control >>= 1
    except IndexError:
        return None
    return None


def exact_arcade_name_matches(
    romdata: Path, bank_path: Path
) -> list[dict[str, object]]:
    """Match name TIMs after LZ decode, tolerating harmless recompression."""
    bank = bank_path.read_bytes()
    members = decoded_members(romdata / "entry-05.bin")
    wanted: dict[str, list[int]] = {}
    for index, _, decoded in members:
        wanted.setdefault(sha256(decoded), []).append(index)
    found: dict[str, list[tuple[int, int]]] = {}
    # The verified System 12 name-stream run is contained in this one-MiB
    # window.  Bounding the scan avoids treating arbitrary ROM bytes as huge
    # malformed streams.
    for offset in range(0x10E0000, min(0x10F0000, len(bank))):
        candidate = decompress_at_bounded(bank, offset, 1024)
        if candidate is None:
            continue
        decoded, used = candidate
        digest = sha256(decoded)
        if digest in wanted:
            found.setdefault(digest, []).append((offset, used))
    rows = []
    for digest, indices in wanted.items():
        for offset, used in found.get(digest, []):
            rows.append(
                {
                    "members": indices,
                    "labels": [UI_NAMES[5].get(i, "unmapped") for i in indices],
                    "arcade_bank_offset": offset,
                    "compressed_size": used,
                    "decoded_sha256": digest,
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extract",
        type=Path,
        default=Path("workspace/tekken5-arcade-history"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("workspace/tekken5-t3-deep-probe"),
    )
    parser.add_argument("--arcade-bank", type=Path)
    args = parser.parse_args()
    romdata = args.extract / "tekken3" / "romdata"
    args.output.mkdir(parents=True, exist_ok=True)
    tim_tool.VRAM_HEIGHT = 1024
    report: dict[str, object] = {
        "warning": (
            "Labels describe the confirmed UI index mapping. Model archive member "
            "numbers use a separate paired-costume order and are not character IDs."
        ),
        "ui": ui_census(romdata, args.output),
        "descriptor_stages": descriptor_stage_census(
            args.extract / "executables" / "tekken3.elf"
        ),
        "model_textures": model_texture_census(romdata, args.output),
        "texture_packs": texture_pack_census(romdata, args.output),
        "misc_graphics": generic_tim_census(romdata, args.output),
    }
    if args.arcade_bank:
        report["exact_arcade_matches"] = exact_arcade_matches(
            romdata, args.arcade_bank
        )
        report["exact_arcade_name_matches"] = exact_arcade_name_matches(
            romdata, args.arcade_bank
        )
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.output / 'report.json'} and contact sheets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

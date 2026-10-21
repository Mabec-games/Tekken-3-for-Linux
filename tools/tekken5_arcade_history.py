"""Inspect and extract Tekken 5 PS2 Arcade History data.

The retail disc stores the Arcade History launcher and payloads in
TK5DATA3.BIN (duplicated as TK5DATA5.BIN).  This tool parses the outer
sector-aligned table, the named payload directory, and the nested ARC tables
used by Tekken 3.  It also implements the small LZ decompressor embedded in
TK5DATA4.BIN so the Tekken 1/2/3 executables can be recovered reproducibly.

Keep extracted copyrighted data under the repository's ignored workspace/
directory.  The tool refuses to overwrite an existing output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path


class ProbeError(RuntimeError):
    """Raised when an input does not match the expected container layout."""


@dataclass(frozen=True)
class Slice:
    index: int
    offset: int
    size: int
    end: int


@dataclass(frozen=True)
class NamedSlice:
    index: int
    name: str
    offset: int
    size: int


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ProbeError(f"u32 read outside input at 0x{offset:x}")
    return struct.unpack_from("<I", data, offset)[0]


def parse_linear_archive(data: bytes) -> list[Slice]:
    """Parse a count/header followed by (size, next-offset) pairs."""
    if len(data) < 8:
        raise ProbeError("linear archive is shorter than its header")
    count = _u32(data, 0)
    first_offset = _u32(data, 4)
    minimum_header = 8 + count * 8
    if not 0 < count < 10_000:
        raise ProbeError(f"implausible entry count {count}")
    if not minimum_header <= first_offset <= len(data):
        raise ProbeError(
            f"invalid first offset 0x{first_offset:x} for {count} entries"
        )

    result: list[Slice] = []
    offset = first_offset
    for index in range(count):
        size = _u32(data, 8 + index * 8)
        raw_end = _u32(data, 12 + index * 8)
        end = len(data) if index == count - 1 and raw_end in (0, 0xFFFFFFFF) else raw_end
        if offset + size > end or end > len(data):
            raise ProbeError(
                f"entry {index} has invalid range 0x{offset:x}+0x{size:x} -> 0x{end:x}"
            )
        result.append(Slice(index, offset, size, end))
        offset = end
    return result


def parse_named_directory(data: bytes) -> list[NamedSlice]:
    """Parse the variable-width named directory inside outer entry 7."""
    count = _u32(data, 0)
    if not 0 < count < 1_000:
        raise ProbeError(f"implausible named-directory count {count}")
    position = 4
    result: list[NamedSlice] = []
    for index in range(count):
        record_size = _u32(data, position)
        body_start = position + 4
        body_end = body_start + record_size
        if record_size < 12 or body_end > len(data):
            raise ProbeError(f"invalid named record {index} at 0x{position:x}")
        body = data[body_start:body_end]
        raw_name = body[:-8].split(b"\0", 1)[0]
        try:
            name = raw_name.decode("ascii")
        except UnicodeDecodeError as error:
            raise ProbeError(f"record {index} has a non-ASCII name") from error
        offset, size = struct.unpack_from("<II", body, record_size - 8)
        if offset + size > len(data):
            raise ProbeError(f"named entry {name!r} extends outside its container")
        result.append(NamedSlice(index, name, offset, size))
        position = body_end
    return result


def decompress_arcade_executable(source: bytes) -> bytes:
    """Decode the flag-byte/11-bit-distance LZ stream used by entries 0-6."""
    source_pos = 0
    output = bytearray()
    while source_pos < len(source):
        control = source[source_pos]
        source_pos += 1
        if control == 0:
            break
        if control < 2:
            continue
        while True:
            if control & 1:
                if source_pos >= len(source):
                    raise ProbeError("literal extends beyond compressed stream")
                output.append(source[source_pos])
                source_pos += 1
            else:
                if source_pos + 2 > len(source):
                    raise ProbeError("match token extends beyond compressed stream")
                token = (source[source_pos] << 8) | source[source_pos + 1]
                source_pos += 2
                distance = token & 0x7FF or 0x800
                length = (token >> 11) & 0x1F or 0x20
                if distance > len(output):
                    raise ProbeError(
                        f"match distance 0x{distance:x} exceeds output size 0x{len(output):x}"
                    )
                for _ in range(length):
                    output.append(output[-distance])
            control >>= 1
            if control < 2:
                break
    return bytes(output)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract(data_path: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise ProbeError(f"output already exists: {output}")
    data = data_path.read_bytes()
    outer = parse_linear_archive(data)
    if len(outer) < 8:
        raise ProbeError("expected at least eight outer entries")

    output.mkdir(parents=True)
    executables_dir = output / "executables"
    executables_dir.mkdir()
    executable_names = ["tekken1.elf", "tekken2.elf", "tekken3.elf"]
    executable_report = []
    for entry, name in zip(outer[:3], executable_names, strict=True):
        decoded = decompress_arcade_executable(
            data[entry.offset : entry.offset + entry.size]
        )
        if not decoded.startswith(b"\x7fELF"):
            raise ProbeError(f"decoded {name} does not begin with ELF magic")
        (executables_dir / name).write_bytes(decoded)
        executable_report.append(
            {"name": name, "size": len(decoded), "sha256": _sha256(decoded)}
        )

    payload_entry = outer[7]
    payload = data[payload_entry.offset : payload_entry.offset + payload_entry.size]
    named = parse_named_directory(payload)
    named_by_name = {entry.name: entry for entry in named}
    if "romdata.arc" not in named_by_name:
        raise ProbeError("Tekken 3 romdata.arc was not found")
    tekken3_start = named_by_name["romdata.arc"].index

    tekken3_dir = output / "tekken3"
    tekken3_dir.mkdir()
    tekken3_report = []
    for entry in named[tekken3_start:]:
        contents = payload[entry.offset : entry.offset + entry.size]
        (tekken3_dir / entry.name).write_bytes(contents)
        tekken3_report.append(
            {
                **asdict(entry),
                "sha256": _sha256(contents),
                "magic": contents[:8].hex(),
            }
        )

    romdata = (tekken3_dir / "romdata.arc").read_bytes()
    romdata_entries = parse_linear_archive(romdata)
    romdata_dir = tekken3_dir / "romdata"
    romdata_dir.mkdir()
    romdata_report = []
    for entry in romdata_entries:
        contents = romdata[entry.offset : entry.offset + entry.size]
        name = f"entry-{entry.index:02d}.bin"
        (romdata_dir / name).write_bytes(contents)
        child_count = None
        try:
            child_count = len(parse_linear_archive(contents))
        except ProbeError:
            pass
        romdata_report.append(
            {
                **asdict(entry),
                "name": name,
                "sha256": _sha256(contents),
                "child_count": child_count,
            }
        )

    report: dict[str, object] = {
        "source": str(data_path.resolve()),
        "source_size": len(data),
        "source_sha256": _sha256(data),
        "outer_entries": [asdict(entry) for entry in outer],
        "named_entries": [asdict(entry) for entry in named],
        "executables": executable_report,
        "tekken3_entries": tekken3_report,
        "romdata_entries": romdata_report,
    }
    (output / "manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data3", type=Path, help="path to TK5DATA3.BIN")
    parser.add_argument("output", type=Path, help="fresh output directory")
    args = parser.parse_args()
    try:
        report = extract(args.data3, args.output)
    except (OSError, ProbeError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

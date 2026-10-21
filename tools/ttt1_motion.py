#!/usr/bin/env python3
"""Decode System 12 TTT1 joint motion from a verified local ROM bank.

Format recovered from the arcade decoder at 0x80105B34. This exports poses
and source records; it does not claim to convert combat logic to Tekken 3.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct

try:
    from .prepare_jun_import import BANK_SHA, RAM_SHA, verified
except ImportError:
    from prepare_jun_import import BANK_SHA, RAM_SHA, verified

ROOT = Path(__file__).resolve().parents[1]
JIN_RAM_SHA = "3e57e7a50b29ddb8104f990afc48e60dd1665f94cacef975550e74e6b47712d5"
CHANNELS = 57
JUN_IDLE = 0x102B58


def decode(bank: bytes, base: int, frame: int, channels: int = CHANNELS) -> list[int]:
    """Return original unsigned 16-bit channel values for one animation frame.

The first three channels are polar root motion (heading, height, distance),
followed by 18 XYZ joint rotations. Values deliberately retain their original
integer precision and wraparound. Conversion to a target skeleton is separate.
"""
    if frame < 0 or not 1 <= channels <= CHANNELS:
        raise ValueError("Invalid frame or channel count")
    if base < 0 or base + 0x130 > len(bank):
        raise ValueError("Truncated animation header")
    count = bank[base]
    if not count:
        raise ValueError("Animation has no frames")
    if frame + 1 >= count:
        return list(struct.unpack_from(f"<{channels}H", bank, base + 0x74))
    values = list(struct.unpack_from(f"<{channels}H", bank, base + 2))
    if frame == 0:
        return values
    block, within = divmod(frame - 1, 16)
    cursor = base + struct.unpack_from("<H", bank, base + 0xE6 + block * 2)[0] * 2
    for channel in range(channels):
        initial = cursor
        bits = remaining = consumed = 0

        def take(n: int) -> int:
            nonlocal bits, remaining, cursor, consumed
            while remaining < n:
                if cursor < 0 or cursor + 2 > len(bank):
                    raise ValueError("Truncated animation channel")
                bits |= struct.unpack_from("<H", bank, cursor)[0] << remaining
                cursor += 2
                remaining += 16
            value = bits & ((1 << n) - 1)
            bits >>= n
            remaining -= n
            consumed += n
            return value

        span = take(4)
        next_channel = initial + span * 2
        if not span or next_channel > len(bank):
            raise ValueError("Invalid channel block span")
        shift = 2 if channel in (1, 2) else 4
        value = values[channel]
        repeat = code = 0
        for _ in range(within + 1):
            if repeat:
                repeat -= 1
            else:
                code = take(4)
                if code >= 8:
                    repeat = (take(4) + 1) & 15
                    code -= 8
            if code == 7:
                value = take(12) << shift
            elif code:
                width, bias = {1: (6, -84), 2: (4, -20), 3: (2, -4),
                               4: (2, 1), 5: (4, 5), 6: (6, 21)}[code]
                value += (take(width) + bias) << shift
            if consumed > span * 16:
                raise ValueError("Animation bits exceed the declared channel span")
        values[channel] = value & 65535
        cursor = next_channel
    return values


def validate_capture(bank: bytes, capture: Path) -> dict:
    """Compare against poses sampled at return from the original MAME decoder."""
    poses = samples = 0
    clips = set()
    for row in csv.DictReader(capture.open(encoding="utf-8")):
        source, frame, channels = int(row["source"], 16), int(row["frame"]), int(row["channels"])
        actual = [int(x, 16) for x in row["pose"].split()]
        decoded = decode(bank, source, frame, channels)
        if actual != decoded:
            raise ValueError(f"Arcade pose mismatch: clip 0x{source:x}, frame {frame}")
        clips.add(source)
        poses += 1
        samples += channels
    if not poses:
        raise ValueError("Capture contains no decoded poses")
    return dict(poses=poses, channel_samples=samples, clips=len(clips), mismatches=0,
                capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest())


def export(work: Path, capture: Path | None = None) -> dict:
    bank = verified(work / "ttt1/bankedroms.bin", BANK_SHA)
    jun = verified(work / "jun-select-ram.bin", RAM_SHA)
    jin = verified(work / "jin-select-ram.bin", JIN_RAM_SHA)
    aliases = struct.unpack_from("<5515I", jun, 0x2A7350)
    reference = struct.unpack_from("<5515I", jin, 0x2A7350)
    # Character-dependent entries only. Common reactions and Jin's missing
    # entries must not be mislabelled as unique Jun attacks.
    changed = [(i, a) for i, (a, b) in enumerate(zip(aliases, reference))
               if a != b and a != 0x8009374C]
    records = []
    for address in sorted({a for _, a in changed}):
        fields = struct.unpack_from("<13I", jun, address & 0x3FFFFF)
        records.append(dict(address=address, aliases=[i for i, a in changed if a == address],
                            animation=fields[0], raw_words=list(fields)))
    sources = sorted({r["animation"] for r in records})
    out = work / "jun/motion"
    out.mkdir(parents=True, exist_ok=True)
    clips = []
    for source in sources:
        count = bank[source]
        poses = b"".join(struct.pack("<57H", *decode(bank, source, f)) for f in range(count))
        name = f"{source:08x}.poses"
        (out / name).write_bytes(poses)
        if source == JUN_IDLE:
            (work / "jun/Jun-TTT1-idle.poses").write_bytes(poses)
        clips.append(dict(source=source, frames=count, channels=57, file=name,
                          sha256=hashlib.sha256(poses).hexdigest()))
    report = dict(schema_version=1, source_bank_sha256=BANK_SHA, records=records, clips=clips,
                  total_frames=sum(c["frames"] for c in clips),
                  status="Decoded arcade motion; convert_jun_moves.py performs the solo combat conversion",
                  unresolved=["Tag-only transitions are excluded from the solo conversion"])
    if capture:
        report["arcade_validation"] = validate_capture(bank, capture)
    (out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work-dir", type=Path, default=ROOT / "workspace/jun-import")
    p.add_argument("--validate-capture", type=Path)
    args = p.parse_args()
    report = export(args.work_dir.resolve(), args.validate_capture)
    print(f"Exported {len(report['clips'])} clips / {report['total_frames']} frames, "
          f"referenced by {len(report['records'])} character-dependent records")
    if "arcade_validation" in report:
        print(json.dumps(report["arcade_validation"]))


if __name__ == "__main__":
    main()

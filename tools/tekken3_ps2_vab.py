"""Carve PlayStation VAB sound banks embedded in Tekken 5's Tekken 3 ELF.

The Arcade History port stores each bank as ``VB data + VH header``.  This is
the reverse of a conventional VAB file, so ordinary audio tools do not find the
banks directly.  This utility validates the Sony headers and SPU-ADPCM payloads
with the project's existing VAB parser, then writes conventional ``VH + VB``
analysis copies under an ignored output directory.

The output contains copyrighted game audio.  Keep it under ``workspace/`` and
do not commit or redistribute it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from tools import vab_tool
except ModuleNotFoundError:  # Direct execution: ``python tools/tekken3_ps2_vab.py``.
    import vab_tool  # type: ignore[no-redef]


class CarveError(RuntimeError):
    """Raised when the input or requested output is unsafe or unsupported."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ps1_hash_index(audit_path: Path | None) -> dict[str, int]:
    if audit_path is None:
        return {}
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        pairs = audit["pairs"]
        return {
            pair["reconstructed_vab"]["sha256"]: pair["vh_id"]
            for pair in pairs
        }
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise CarveError(f"cannot read PS1 VAB audit {audit_path}: {error}") from error


def carve(elf_path: Path, output: Path, audit_path: Path | None = None) -> dict[str, object]:
    if output.exists():
        raise CarveError(f"output already exists: {output}")
    try:
        data = elf_path.read_bytes()
    except OSError as error:
        raise CarveError(f"cannot read {elf_path}: {error}") from error
    if not data.startswith(b"\x7fELF"):
        raise CarveError("input does not begin with ELF magic")

    ps1_by_hash = _ps1_hash_index(audit_path)
    banks: list[dict[str, object]] = []
    position = 0
    while True:
        vh_offset = data.find(b"pBAV", position)
        if vh_offset < 0:
            break
        position = vh_offset + 1

        # The strict parser needs the exact VH size.  Program count is the
        # second 16-bit field at header offset 0x10.
        if vh_offset + 0x14 > len(data):
            continue
        program_count = int.from_bytes(data[vh_offset + 0x12 : vh_offset + 0x14], "little")
        vh_size = 0xA20 + program_count * 0x200
        if vh_offset + vh_size > len(data):
            continue
        vh_data = data[vh_offset : vh_offset + vh_size]
        try:
            header = vab_tool.parse_vh(vh_data)
        except vab_tool.VabToolError:
            continue

        vb_offset = vh_offset - header.vb_size
        if vb_offset < 0:
            continue
        vb_data = data[vb_offset:vh_offset]
        try:
            vab_tool.validate_vb(vb_data, header)
        except vab_tool.VabToolError:
            continue

        conventional = vh_data + vb_data
        sha256 = _sha256(conventional)
        banks.append(
            {
                "index": len(banks),
                "vb_offset": vb_offset,
                "vh_offset": vh_offset,
                "vb_size": len(vb_data),
                "vh_size": len(vh_data),
                "size": len(conventional),
                "program_count": header.program_count,
                "tone_count": header.tone_count,
                "vag_count": header.vag_count,
                "sha256": sha256,
                "exact_ps1_vh_id": ps1_by_hash.get(sha256),
                "data": conventional,
            }
        )

    if not banks:
        raise CarveError("no structurally valid embedded VAB banks were found")

    output.mkdir(parents=True)
    report_banks = []
    for bank in banks:
        contents = bank.pop("data")
        name = f"bank-{bank['index']:02d}.vab"
        (output / name).write_bytes(contents)
        report_banks.append({**bank, "name": name})

    report: dict[str, object] = {
        "source": str(elf_path.resolve()),
        "source_size": len(data),
        "source_sha256": _sha256(data),
        "ps1_audit": str(audit_path.resolve()) if audit_path else None,
        "bank_count": len(report_banks),
        "exact_ps1_match_count": sum(
            bank["exact_ps1_vh_id"] is not None for bank in report_banks
        ),
        "banks": report_banks,
    }
    (output / "manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path, help="extracted Tekken 3 PS2 ELF")
    parser.add_argument("output", type=Path, help="fresh ignored output directory")
    parser.add_argument(
        "--ps1-audit",
        type=Path,
        help="optional vab_tool.py audit JSON for exact PS1 bank comparison",
    )
    args = parser.parse_args()
    try:
        report = carve(args.elf, args.output, args.ps1_audit)
    except CarveError as error:
        parser.error(str(error))
    print(
        f"Carved {report['bank_count']} VABs; "
        f"{report['exact_ps1_match_count']} exact PS1 matches."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build a full Easy Setup ZIP from this source tree and a verified prior bundle.

Example:
  python scripts/create_easy_setup_release.py --base-zip v0.1.2-Easy-Setup.zip

The prior bundle supplies the portable Python runtime and bootstrap executable.
All game, launcher, mod, and framework source comes from this checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "launcher"))
import update_backend as updater

BASE_VERSION = "v0.1.2-easy-setup"
BASE_SHA256 = "807ebc7e88d870afa10d69a7517091bad1e2cd37bd2c6ff94aecca9194438ca9"
SOURCE_DIRS = ("src", "tools", "mods", "native", "launcher_assets", "seeds", "psxrecomp", "recomp-ui", "launcher")
ROOT_FILES = ("VERSION", "CMakeLists.txt", "codegen_setup.c", "codegen_setup.h", "game.toml",
              "README.md", "RELEASE-NOTES.md", "MODDING.md", "Outfit-Slots.md", "LAUNCHER.md",
              "framework_pins.txt", "catalog_identity.json", "symbols.toml")
REQUIRED = ("VERSION", "Play Tekken 3.exe", "game.toml", ".runtime/python/python.exe",
            "launcher/easy_launcher.py", "launcher/setup_backend.py", "launcher/update_backend.py",
            "launcher/tools.lock.json")
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "build", "build-release", "workspace", ".setup"}
PRIVATE_NAMES = {"keybinds.ini", "settings.toml", "state.toml", "bios.cfg", "disc.cfg", ".mcp.json"}
PRIVATE_SUFFIXES = (".mcd", ".mcr", ".sav", ".cue", ".iso", ".chd", ".jui", ".juv",
                    ".jmv", ".3dm", ".poses", ".4bpp", ".log", ".dmp", ".key")


def publishable_source(relative: Path) -> bool:
    parts = tuple(part.lower() for part in relative.parts)
    name = parts[-1]
    return not (any(part in SKIP_PARTS for part in parts)
                or name in PRIVATE_NAMES or name.startswith(".env")
                or name.endswith(PRIVATE_SUFFIXES) or ".mcd." in name or ".mcr." in name
                or name.endswith(".pyc"))


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def source_files(tag: str):
    for name in (*ROOT_FILES, f"CHANGELOG_{tag}.md"):
        path = ROOT / name
        if path.is_file():
            yield name, path
    for folder in SOURCE_DIRS:
        base = ROOT / folder
        if not base.is_dir():
            raise SystemExit(f"Required source directory is missing: {base}")
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(ROOT)
            if not publishable_source(relative):
                continue
            yield relative.as_posix(), path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-zip", required=True, type=Path,
                        help="Official v0.1.2 Easy Setup ZIP used only for portable runtime/bootstrap")
    parser.add_argument("--output-dir", default=ROOT / "dist", type=Path)
    args = parser.parse_args()
    archive = args.base_zip.resolve()
    if digest(archive) != BASE_SHA256:
        raise SystemExit("Base archive SHA-256 does not match the official v0.1.2 package.")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if updater.version_tuple(version) is None or updater.version_tuple(version) <= updater.version_tuple(BASE_VERSION):
        raise SystemExit("VERSION must be newer than the v0.1.2 base package.")
    tag = "v" + version.lstrip("v")
    changelog = f"CHANGELOG_{tag}.md"
    if not (ROOT / changelog).is_file() or not (ROOT / changelog).read_text(encoding="utf-8").strip():
        raise SystemExit(f"Exact patch changelog is missing: {changelog}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"Tekken3Recompiled-{tag}-Easy-Setup.zip"
    with tempfile.TemporaryDirectory(prefix="tekken3-package-") as temp:
        stage = Path(temp) / "stage"
        base_manifest = Path(temp) / "base-manifest.json"
        with zipfile.ZipFile(archive) as zipped:
            base_manifest.write_bytes(zipped.read("RELEASE-MANIFEST.json"))
        updater.report = lambda *_args, **_kwargs: None
        updater.stage_archive(archive, base_manifest, stage, BASE_VERSION)
        current = dict(source_files(tag))
        for path in stage.rglob("*"):
            if path.is_file():
                relative = path.relative_to(stage).as_posix()
                # The prior Easy Setup bundle ships two prebuilt recompiler
                # tools under psxrecomp/recompiler/build; keep those binaries.
                if (relative.split("/", 1)[0] in SOURCE_DIRS and relative not in current
                        and not relative.startswith("psxrecomp/recompiler/build/")):
                    path.unlink()
        for name, source in current.items():
            updater.safe_name(name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        for name in (*REQUIRED, changelog):
            if not (stage / name).is_file():
                raise SystemExit(f"Package is missing {name}")
        # A future release must not accidentally retain the previous patch label.
        if (stage / "VERSION").read_text(encoding="utf-8").strip() != version:
            raise SystemExit("Package VERSION does not match this checkout.")
        files = []
        for path in sorted(stage.rglob("*")):
            if path.is_file() and path.name != "RELEASE-MANIFEST.json":
                name = path.relative_to(stage).as_posix()
                files.append({"path": name, "size": path.stat().st_size, "sha256": digest(path)})
        manifest = {"release": tag, "files": files}
        manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        (stage / "RELEASE-MANIFEST.json").write_bytes(manifest_bytes)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7,
                             allowZip64=True) as zipped:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    zipped.write(path, path.relative_to(stage).as_posix())
        manifest_output = args.output_dir / "RELEASE-MANIFEST.json"
        manifest_output.write_bytes(manifest_bytes)
    sums = args.output_dir / "SHA256SUMS.txt"
    sums.write_text(f"{digest(output)}  {output.name}\n{digest(manifest_output)}  {manifest_output.name}\n",
                    encoding="utf-8")
    print(f"Created {output}")
    print(f"Created {manifest_output}")
    print(f"Created {sums}")
    print(f"SHA-256 {digest(output)}")


if __name__ == "__main__":
    main()

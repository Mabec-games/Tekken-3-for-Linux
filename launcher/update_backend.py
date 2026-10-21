"""GitHub release checker and in-place Easy Setup updater.

The installed Easy Setup bundle supplies its own Python interpreter.  This
worker moves that interpreter outside the application before replacing files.
No disc image, save, generated game data, or local tool download is uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile


REPOSITORY = "Tekken3Linux/Tekken3Recompiled"
API = f"https://api.github.com/repos/{REPOSITORY}/releases"
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".setup"
STATUS = STATE / "update-status.json"
SETTINGS = STATE / "updates.json"
MAX_PACKAGE = 3 * 1024**3
MAX_FILES = 12000
VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$", re.I)


class UpdateError(Exception):
    pass


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def load_json(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def report(phase: str, **extra) -> None:
    save_json(STATUS, {"phase": phase, "at": time.time(), **extra})


def version_tuple(raw: str):
    match = VERSION_RE.fullmatch(raw.strip())
    return tuple(map(int, match.groups())) if match else None


def current_version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as error:
        raise UpdateError("This installation has no VERSION file.") from error


def request_json(url: str) -> dict | list:
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Tekken3Recompiled-Updater",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise UpdateError("Could not contact GitHub. Check your connection and try again.") from error


def full_package(release: dict) -> tuple[dict, dict] | None:
    assets = {item.get("name", "").lower(): item for item in release.get("assets", [])}
    version = version_tuple(str(release.get("tag_name", "")))
    packages = [item for name, item in assets.items()
                if (match := re.fullmatch(r"tekken3recompiled-v(\d+)\.(\d+)\.(\d+)-easy-setup\.zip", name))
                and tuple(map(int, match.groups())) == version]
    manifest = assets.get("release-manifest.json")
    if len(packages) != 1 or not manifest:
        return None
    if not all(re.fullmatch(r"sha256:[0-9a-fA-F]{64}", x.get("digest", ""))
               for x in (packages[0], manifest)):
        return None
    return packages[0], manifest


def select_release(releases: list, minimum: str, wanted: str | None = None) -> tuple[dict, dict, dict] | None:
    baseline = version_tuple(minimum)
    if baseline is None:
        raise UpdateError("The installed version is invalid.")
    choices = []
    for release in releases:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name", ""))
        number = version_tuple(tag)
        if number is None or number <= baseline or (wanted and tag != wanted):
            continue
        package = full_package(release)
        if package:
            choices.append((number, release, *package))
    if not choices:
        return None
    _, release, archive, manifest = max(choices, key=lambda row: row[0])
    return release, archive, manifest


def releases() -> list:
    result = request_json(API + "?per_page=100")
    if not isinstance(result, list):
        raise UpdateError("GitHub returned an unexpected release list.")
    return result


def check() -> None:
    installed = current_version()
    report("checking", installed=installed)
    selected = select_release(releases(), installed)
    if selected is None:
        report("current", installed=installed, message="You're on the latest available patch.")
        return
    release, archive, _ = selected
    report("available", installed=installed, version=release["tag_name"],
           name=release.get("name") or release["tag_name"],
           notes=release.get("body") or "No patch notes were published.",
           size=archive["size"], message="Update available")


def download(asset: dict, destination: Path, label: str) -> Path:
    url = str(asset.get("browser_download_url", ""))
    if not url.startswith(f"https://github.com/{REPOSITORY}/releases/download/"):
        raise UpdateError("The release asset URL is unexpected.")
    expected = asset["digest"].split(":", 1)[1].lower()
    size = int(asset["size"])
    if size <= 0 or size > MAX_PACKAGE:
        raise UpdateError("The release asset size is invalid.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    received = 0
    request = urllib.request.Request(url, headers={"User-Agent": "Tekken3Recompiled-Updater"})
    try:
        with urllib.request.urlopen(request, timeout=60) as source, destination.open("wb") as output:
            while block := source.read(1024 * 1024):
                received += len(block)
                if received > size:
                    raise UpdateError("The release download exceeded its advertised size.")
                digest.update(block)
                output.write(block)
                report("downloading", message=label, received=received, total=size)
    except (OSError, urllib.error.URLError) as error:
        raise UpdateError("The download was interrupted. Try again.") from error
    if received != size or digest.hexdigest() != expected:
        raise UpdateError("The release download failed its SHA-256 check.")
    return destination


def safe_name(name: str) -> str:
    if "\\" in name or "\x00" in name or ":" in name or any(ord(ch) < 32 for ch in name):
        raise UpdateError("The release contains an unsafe path.")
    posix, windows = PurePosixPath(name), PureWindowsPath(name)
    if (posix.is_absolute() or windows.is_absolute() or windows.drive
            or any(part in ("", ".", "..") for part in posix.parts)
            or any(part.rstrip(" .") != part or part.split(".", 1)[0].upper() in
                   {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                    *(f"LPT{i}" for i in range(1, 10))} for part in posix.parts)):
        raise UpdateError("The release contains an unsafe path.")
    if posix.parts[0].lower() in (".git", ".setup", ".tools", "build-release", "disc", "workspace"):
        raise UpdateError("The release attempts to replace personal or generated data.")
    return posix.as_posix()


def stage_archive(archive: Path, manifest_path: Path, stage: Path, tag: str) -> list[str]:
    manifest = load_json(manifest_path)
    if manifest.get("release") != tag or not isinstance(manifest.get("files"), list):
        raise UpdateError("The release manifest does not match this patch.")
    entries = {}
    for row in manifest["files"]:
        name = safe_name(row["path"])
        if name.casefold() in entries or not re.fullmatch(r"[a-fA-F0-9]{64}", row["sha256"]):
            raise UpdateError("The release manifest contains duplicate or invalid files.")
        entries[name.casefold()] = (name, int(row["size"]), row["sha256"].lower())
    if not entries or len(entries) > MAX_FILES:
        raise UpdateError("The release manifest has an invalid file count.")
    seen = set()
    total = 0
    embedded_manifest = False
    with zipfile.ZipFile(archive) as zipped:
        files = [info for info in zipped.infolist() if not info.is_dir()]
        if len(files) not in (len(entries), len(entries) + 1):
            raise UpdateError("The release archive does not match its manifest.")
        for index, info in enumerate(files, 1):
            name = safe_name(info.filename)
            if name == "RELEASE-MANIFEST.json" and name.casefold() not in entries:
                if embedded_manifest or info.file_size > 4 * 1024 * 1024:
                    raise UpdateError("The embedded release manifest is invalid.")
                content = zipped.read(info)
                try:
                    identical = json.loads(content) == manifest
                except ValueError:
                    identical = False
                if not identical:
                    raise UpdateError("The embedded release manifest disagrees with GitHub's manifest.")
                target = stage / name
                target.write_bytes(content)
                embedded_manifest = True
                continue
            key = name.casefold()
            if (key in seen or key not in entries or entries[key][0] != name
                    or info.file_size != entries[key][1]
                    or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise UpdateError("The release archive contains an unexpected file.")
            total += info.file_size
            if total > MAX_PACKAGE:
                raise UpdateError("The release archive is too large.")
            target = stage.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            with zipped.open(info) as source, target.open("wb") as output:
                while block := source.read(1024 * 1024):
                    digest.update(block)
                    output.write(block)
            if digest.hexdigest() != entries[key][2]:
                raise UpdateError(f"A file failed verification: {name}")
            seen.add(key)
            if index == 1 or index % 40 == 0 or index == len(files):
                report("verifying", message=f"Verifying files: {index} / {len(files)}",
                       received=index, total=len(files))
    if len(seen) != len(entries) or len(files) != len(entries) + int(embedded_manifest):
        raise UpdateError("The release archive is missing a manifest file.")
    names = [entries[key][0] for key in sorted(entries)]
    if embedded_manifest:
        names.append("RELEASE-MANIFEST.json")
    return names


def wait_for_parent(pid: int) -> None:
    if pid <= 0 or os.name != "nt":
        return
    import ctypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x00100000, 0, pid)
    if handle:
        try:
            if kernel.WaitForSingleObject(handle, 120000) != 0:
                raise UpdateError("The game did not close in time. Please try again.")
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))


def rebuild() -> None:
    backend_path = ROOT / "launcher" / "setup_backend.py"
    inputs = load_json(STATE / "last-inputs.json")
    disc = inputs.get("disc", "")
    if not backend_path.is_file() or not disc or not Path(disc).is_file():
        raise UpdateError("Updated files are installed, but the saved disc setup is missing. Open Play Tekken 3.exe to finish setup.")
    command = [sys.executable, "-I", str(backend_path), "--disc", disc]
    if inputs.get("jun"):
        if not all(Path(inputs.get(key, "")).is_file() for key in ("ttt1", "t3_arcade")):
            raise UpdateError("Updated files are installed, but Jun's saved source files are missing. Open Play Tekken 3.exe to finish setup.")
        command += ["--ttt1", inputs["ttt1"], "--t3-arcade", inputs["t3_arcade"]]
    else:
        command.append("--no-jun")
    report("building", message="Rebuilding the updated game. This may take several minutes.")
    with (STATE / "update-build.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode:
        raise UpdateError("The game rebuild failed. See .setup/update-build.log.")


def apply_files(stage: Path, names: list[str], backup: Path) -> tuple[list[str], list[str]]:
    replaced, added = [], []
    try:
        for name in names:
            source = stage.joinpath(*PurePosixPath(name).parts)
            target = ROOT.joinpath(*PurePosixPath(name).parts)
            old = backup.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != ROOT):
                raise UpdateError("A destination path is a symbolic link.")
            if target.exists():
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, old)
                replaced.append(name)
            else:
                added.append(name)
            os.replace(source, target)
        return replaced, added
    except Exception:
        rollback(replaced, added, backup)
        raise


def rollback(replaced: list[str], added: list[str], backup: Path) -> None:
    for name in reversed(added):
        ROOT.joinpath(*PurePosixPath(name).parts).unlink(missing_ok=True)
    for name in reversed(replaced):
        old = backup.joinpath(*PurePosixPath(name).parts)
        if old.is_file():
            os.replace(old, ROOT.joinpath(*PurePosixPath(name).parts))


def install(tag: str, parent_pid: int, restart: bool = True) -> None:
    installed = current_version()
    selected = select_release(releases(), installed, tag)
    if selected is None:
        raise UpdateError("That patch is no longer a newer full release.")
    release, asset, manifest_asset = selected
    STATE.mkdir(exist_ok=True)
    work = STATE / "update-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    replaced, added = [], []
    old_exe = ROOT / "build-release" / "Tekken_3_Recompiled.exe"
    old_ready = STATE / "ready.json"
    runtime_folders = ("mods", "assets", "native")
    try:
        archive = download(asset, work / "package.zip", "Downloading game patch")
        manifest = download(manifest_asset, work / "manifest.json", "Downloading patch manifest")
        names = stage_archive(archive, manifest, work / "stage", tag)
        report("ready-to-apply", message="Files verified. Closing the launcher to install the patch.")
        wait_for_parent(parent_pid)
        backup = work / "backup"
        if old_exe.is_file():
            (work / "old-game").parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_exe, work / "old-game")
        if old_ready.is_file():
            shutil.copy2(old_ready, work / "old-ready.json")
        for folder in runtime_folders:
            source = ROOT / "build-release" / folder
            if source.is_dir():
                shutil.copytree(source, work / "old-runtime" / folder)
        report("installing", message="Installing verified game files")
        replaced, added = apply_files(work / "stage", names, backup)
        rebuild()
        save_json(STATE / "current-patch.json", {
            "version": tag, "name": release.get("name") or tag,
            "notes": release.get("body") or "No patch notes were published.",
            "url": release.get("html_url", ""),
        })
        report("installed", version=tag, message="Patch installed successfully.")
    except Exception:
        if replaced or added:
            rollback(replaced, added, work / "backup")
        if (work / "old-game").is_file():
            os.replace(work / "old-game", old_exe)
        if (work / "old-ready.json").is_file():
            os.replace(work / "old-ready.json", old_ready)
        for folder in runtime_folders:
            previous = work / "old-runtime" / folder
            current = ROOT / "build-release" / folder
            if previous.is_dir():
                if current.exists():
                    os.replace(current, work / ("failed-runtime-" + folder))
                os.replace(previous, current)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if restart:
        bootstrap = ROOT / "Play Tekken 3.exe"
        game = ROOT / "build-release" / "Tekken_3_Recompiled.exe"
        command = [str(bootstrap), "--settings"] if bootstrap.is_file() else [str(game), "--launcher", "--game", str(ROOT / "game.toml")]
        subprocess.Popen(command, cwd=ROOT)


def move_runtime_and_install(tag: str, parent_pid: int) -> None:
    bundled = ROOT / ".runtime" / "python"
    if os.name == "nt" and bundled.is_dir() and Path(sys.executable).resolve().is_relative_to(bundled.resolve()):
        outside = Path(tempfile.mkdtemp(prefix="tekken3-updater-"))
        shutil.copytree(bundled, outside / "python")
        shutil.copy2(__file__, outside / "update_backend.py")
        command = [str(outside / "python" / "python.exe"), "-I", str(outside / "update_backend.py"),
                   "worker", "--root", str(ROOT), "--version", tag, "--parent-pid", str(parent_pid)]
        subprocess.Popen(command, cwd=outside, creationflags=subprocess.CREATE_NO_WINDOW)
        return
    install(tag, parent_pid)


def main() -> int:
    global ROOT, STATE, STATUS, SETTINGS
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "install", "worker"))
    parser.add_argument("--root", type=Path)
    parser.add_argument("--version", default="")
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args()
    if args.root:
        ROOT = args.root.resolve()
        STATE, STATUS, SETTINGS = ROOT / ".setup", ROOT / ".setup" / "update-status.json", ROOT / ".setup" / "updates.json"
    try:
        if args.command == "check":
            check()
        elif args.command == "install":
            move_runtime_and_install(args.version, args.parent_pid)
        else:
            install(args.version, args.parent_pid)
        return 0
    except Exception as error:
        report("error", message=str(error) if isinstance(error, UpdateError) else "Updater stopped unexpectedly. See .setup/update-build.log.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

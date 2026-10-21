#!/usr/bin/env python3
"""Launch the isolated Jun prototype with normal player controls.

Requires the experimental build and local source assets. Combat conversion
is experimental; see the private combat-report.json for remaining limitations.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "psxrecomp/tools"))
import debug_client

MANIFEST = '''format_version = 5
id = "tekken3.character.jun-probe"
version = "1.0.0"
name = "Jun Import Experiment"
author = "Tekken3Recomp"
description = "Jun arcade character and experimental combat conversion."
resolver = "declarative"
save_compatibility = "shared"
[[target]]
game_id = "SLUS-00402"
exe_sha256 = "fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c"
[[feature]]
id = "jun-probe"
name = "Jun Import Experiment"
description = "Jun arcade character and experimental combat conversion."
group = "Characters"
default_enabled = true
[[plugin]]
feature = "jun-probe"
id = "tekken3.jun-probe"
'''


def launch(build: Path, work: Path, headless: bool = False, selector: bool = False, roster: bool = False, team: bool = False, muted: bool = False, renderer: str = 'software', cold_boot: bool = False) -> dict:
    if team:selector=roster=True
    asset_names=['Jun-TTT1-arcade-P1.3dm','Jun-TTT1-arcade-P1.relocs',
                 'Jun-TTT1-arcade-P1.tim','Jun-TTT1-idle.poses','Jun-TTT1-combat.jmv',
                 'Jun-TTT1-voices.juv','Jun-TTT1-tables.jst']
    if roster:asset_names.extend(('Jun-T3-ui.jui','Jun-T3-name.4bpp'))
    asset_names.extend(f'Jun-TTT1-arcade-P{outfit}.{suffix}' for outfit in (2,3)
                       for suffix in ('3dm','relocs','tim'))
    dependencies=[build / "Tekken_3_Recompiled.exe"]
    if not cold_boot:
        dependencies.append(work / ("ps1-saves/openbios/state_80079C70_slot07.pst" if selector else
                                   "ps1-saves/openbios/state_80079C70_slot09.pst"))
    dependencies.extend(work/'jun'/name for name in asset_names)
    for source in dependencies:
        if not source.is_file():
            raise RuntimeError(f"Missing preview dependency: {source}")
    preview = work / ("preview-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    preview.mkdir(parents=True)
    executable = preview / "Tekken3-Jun-Preview.exe"
    shutil.copy2(build / "Tekken_3_Recompiled.exe", executable)
    for source in build.glob("*.dll"):
        shutil.copy2(source, preview / source.name)
    for name in ("bios", "mods"):
        shutil.copytree(build / name, preview / name)
    # Keep the executable and its asset format together while exports/builds
    # continue. Combat loads only after selection, potentially minutes later.
    assets=preview/'jun-assets';assets.mkdir()
    for name in asset_names:shutil.copy2(work/'jun'/name,assets/name)
    if cold_boot:
        (preview / "saves").mkdir()
    else:
        shutil.copytree(work / "ps1-saves", preview / "saves")
    package = preview / "mods/packages/tekken3.character.jun-probe/1.0.0"
    package.mkdir(parents=True, exist_ok=True)
    (package / "manifest.toml").write_text(MANIFEST, encoding="utf-8")
    (preview / "settings.toml").write_text(
        '[video]\nsupersampling=1\n\n[controller]\np1_device="keyboard"\np2_device="none"\n',
        encoding="utf-8")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    args = [str(executable), "--game", str(ROOT / "game.toml"), "--disc",
            str(ROOT / "disc/Tekken 3 (USA).cue"), "--no-launcher", "--renderer", renderer,
            "--debug-port", str(port), "--memcard-dir", str(preview / "saves")]
    if headless:
        args.append("--headless")
    log_path = preview / "preview.log"
    environment=dict(os.environ, TEKKEN3_JUN_ASSETS=str(assets),
                     TEKKEN3_JUN_ROSTER="1" if roster else "0")
    if cold_boot:
        environment.pop('PSX_LOAD_SLOT',None)
    if muted:environment['SDL_AUDIO_DRIVER']='dummy'
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=log,
                                   env=environment,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    query = lambda request: debug_client.query("127.0.0.1", port, request)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Preview exited during startup; see {log_path}")
            try:
                with socket.create_connection(("127.0.0.1", port), .2):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("Preview debug endpoint did not start")
        if not cold_boot:
            result = query(dict(cmd="savestate", op="load", slot=7 if selector else 9))
            if not result.get("ok"):
                raise RuntimeError(f"Could not load the private preview fixture: {result}")
        control = None
        while time.monotonic() < deadline:
            match = re.search(r"Jun probe: control=([0-9A-F]+)", log_path.read_text(errors="replace"))
            if match:
                control = int(match[1], 16)
                break
            time.sleep(.1)
        if control is None:
            raise RuntimeError("Build has no active Jun experimental plugin or its assets failed verification")
        if roster:
            while "Jun roster: registered character 23" not in log_path.read_text(errors="replace"):
                if process.poll() is not None or time.monotonic()>=deadline:
                    raise RuntimeError(f"The extra roster entry did not initialize; see {log_path}")
                time.sleep(.05)
        for address, value in ((control, 0 if selector else 1), (control + 12, 0 if selector else 2)):
            result = query(dict(cmd="write_ram", addr=f"{address:08x}", val=f"{value:02x}"))
            if not result.get("ok"):
                raise RuntimeError(f"Could not activate Jun: {result}")
        while time.monotonic() < deadline:
            if selector:break
            if process.poll() is not None:
                raise RuntimeError(f"Preview exited while importing Jun; see {log_path}")
            if "Jun probe: P1 Jin model header replaced" in log_path.read_text(errors="replace"):
                break
            time.sleep(.1)
        else:
            raise RuntimeError("Jun's model did not activate in the private fight fixture")
        query(dict(cmd="clear_input"))
        if team:
            for address,value in ((0x800afa88,2),(0x800ae224,0),(0x800ae204,10)):
                for offset in range(4 if address==0x800afa88 else 2):
                    result=query(dict(cmd="write_ram",addr=f"{address+offset:08x}",val=f"{value>>(offset*8)&255:02x}"))
                    if not result.get("ok"):raise RuntimeError(f"Could not open Team Battle: {result}")
        info = dict(pid=process.pid, port=port, executable=str(executable), log=str(log_path),assets=str(assets),
                    control=f"{control:08x}",
                    start="cold-boot" if cold_boot else "team" if team else "selector" if selector else "fight",
                    roster=roster,muted=muted,
                    status=("22 fighters: Jun has her own tile, character ID 23 and three outfits (models 52-54); experimental TTT1 combat"
                            if roster else "Legacy Jun import preview; selector uses E / L2 beside Jin"))
        (work / ("headless-session.json" if headless else "preview-session.json")).write_text(json.dumps(info, indent=2) + "\n")
        return info
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        raise


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build-dir", type=Path, default=ROOT / "build-debug-server-lite")
    p.add_argument("--work-dir", type=Path, default=ROOT / "workspace/jun-import")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--cold-boot", action="store_true",help="Boot from disc with empty saves; never load a state")
    p.add_argument("--selector", action="store_true", help="Start at character selection; combine with --roster for Jun's own tile")
    p.add_argument("--roster", action="store_true", help="Test the native extra character entry (requires --selector)")
    p.add_argument("--team", action="store_true", help="Open Team Battle with the extra Jun entry; implies --selector --roster")
    p.add_argument("--muted", action="store_true", help="Use a silent audio device for this preview")
    p.add_argument("--renderer", choices=('software','opengl','vulkan'), default='software')
    args = p.parse_args()
    if args.roster and not (args.selector or args.team):p.error("--roster requires --selector")
    if args.cold_boot and (not args.selector or args.team):p.error("--cold-boot requires --selector and excludes --team")
    print(json.dumps(launch(args.build_dir.resolve(), args.work_dir.resolve(), args.headless,args.selector,args.roster,args.team,args.muted,args.renderer,args.cold_boot), indent=2))


if __name__ == "__main__":
    main()

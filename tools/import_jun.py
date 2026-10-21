#!/usr/bin/env python3
"""Import Jun locally from user-supplied arcade ROMs, then enable her on rebuild."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'workspace/jun-import'

def run(args, **kwargs):
    subprocess.run([str(x) for x in args],check=True,**kwargs)

def choose(title,pattern):
    import tkinter as tk
    from tkinter import filedialog
    window=tk.Tk();window.withdraw()
    value=filedialog.askopenfilename(title=title,filetypes=[('Required file',pattern)])
    window.destroy()
    if not value:raise ValueError('Import cancelled; no files uploaded or downloaded.')
    return Path(value).resolve()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ttt1',type=Path,help='Non-merged tektagt.zip, World TEG2/VER.C1')
    ap.add_argument('--t3-arcade',type=Path,help='Non-merged tekken3.zip, World TET2/VER.E1')
    ap.add_argument('--mame',type=Path,help='MAME 0.289 executable')
    ap.add_argument('--recompiler',type=Path)
    ap.add_argument('--no-rebuild',action='store_true')
    args=ap.parse_args()
    if not (ROOT/'disc/SLUS_004.02').is_file():
        raise ValueError('Run the launcher and Generate & rebuild with your USA Tekken 3 disc first.')
    try:import PIL
    except ImportError:raise ValueError('Install the importer dependency: python -m pip install -r tools/requirements-import.txt')
    import arcade_model_probe as probe
    import prepare_jun_import as prepare, ttt1_motion as motion
    import convert_jun_moves as combat, prepare_jun_voices as voices
    ttt=(args.ttt1 or choose('Select your tektagt.zip (TTT1 arcade)','*.zip')).resolve()
    t3=(args.t3_arcade or choose('Select your tekken3.zip (Tekken 3 arcade)','*.zip')).resolve()
    mame=(args.mame or choose('Select MAME 0.289 executable','*.exe')).resolve()
    candidates=[ROOT/'psxrecomp/recompiler/build/psxrecomp-game.exe',ROOT/'build-recompiler/psxrecomp-game.exe',ROOT/'psxrecomp/recompiler/build/psxrecomp-game']
    emitter=args.recompiler or next((p for p in candidates if p.is_file()),None)
    if not emitter:raise ValueError('The psxrecomp-game emitter is missing. Build the SDK or use the setup release.')
    WORK.mkdir(parents=True,exist_ok=True)
    definitions=json.loads(probe.MANIFEST.read_text())['sets']
    for archive,name,folder in ((ttt,'tektagt','ttt1'),(t3,'tekken3','t3-arcade')):
        print(f'Verifying {name} ROM chips...',flush=True)
        regions,_=probe.reconstruct(archive,definitions[name])
        out=WORK/folder;out.mkdir(exist_ok=True)
        for key,data in regions.items():(out/(key.replace(':','_')+'.bin')).write_bytes(data)
    # A private fresh directory prevents reads/writes to the player's emulator saves.
    capture=Path(tempfile.mkdtemp(prefix='local-capture-',dir=WORK))
    roms=capture/'roms';roms.mkdir()
    shutil.copyfile(ttt,roms/'tektagt.zip')
    print('Capturing verified arcade tables in a muted MAME run (about one minute)...',flush=True)
    run([mame,'tektagt','-rompath',roms,'-video','none','-sound','none','-nothrottle',
         '-skip_gameinfo','-autoboot_script',ROOT/'tools/capture_jun_import.lua','-autoboot_delay','0',
         '-nvram_directory',capture/'nvram','-cfg_directory',capture/'cfg','-seconds_to_run','50'],
        cwd=capture,timeout=240,
        **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
    for name,expected in (('jun-select-ram.bin',prepare.RAM_SHA),('jin-select-ram.bin',motion.JIN_RAM_SHA)):
        prepare.verified(capture/name,expected)
        shutil.copyfile(capture/name,WORK/name)
    print('Converting model, solo moves, throws, victories, voices and selector artwork...',flush=True)
    prepare.prepare(WORK,Path(emitter).resolve())
    motion.export(WORK)
    combat.build(WORK)
    voices.build(WORK)
    run([sys.executable,ROOT/'tools/prepare_jun_ui.py'],cwd=ROOT)
    expected=json.loads((ROOT/'tools/data/jun_runtime_hashes.json').read_text())
    for name,digest in expected.items():
        if hashlib.sha256((WORK/'jun'/name).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'{name}: converted output differs from the tested showcase version; rebuild stopped.')
    print(f'All {len(expected)} Jun runtime files match the tested version (three arcade outfits).',flush=True)
    if not args.no_rebuild:
        sys.path.insert(0,str(ROOT/'psxrecomp/tools'))
        from toolchain_pack import resolve_toolchain_bin, activate_toolchain_bin
        toolchain=resolve_toolchain_bin(ROOT)
        if toolchain:activate_toolchain_bin(toolchain)
        cmake=shutil.which('cmake')
        if not cmake:
            cmake=next((str(p) for p in (ROOT/'toolchain/bin/cmake.exe',ROOT/'toolchain/bin/cmake') if p.is_file()),None)
        if not cmake:raise ValueError('Import succeeded. Put the setup toolchain cmake on PATH, then run: cmake -S . -B build-release -DTEKKEN3_JUN_EXPERIMENTAL=ON && cmake --build build-release --target psx-runtime')
        run([cmake,'-S',ROOT,'-B',ROOT/'build-release','-DTEKKEN3_JUN_EXPERIMENTAL=ON'])
        run([cmake,'--build',ROOT/'build-release','--target','psx-runtime','-j','8'])
    print('Jun import complete. Select the Jun package in the launcher Mods tab.',flush=True)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print(f'Import failed: {error}',file=sys.stderr);sys.exit(1)

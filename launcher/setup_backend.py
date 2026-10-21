"""Local first-run setup. Downloads only pinned tools; game data stays local."""
from __future__ import annotations
from pathlib import Path, PureWindowsPath
import argparse, hashlib, json, os, re, shutil, struct, subprocess, sys, time
import urllib.request, urllib.error, zipfile

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.setup'
BUILD=ROOT/'build-release'
EXE=BUILD/'Tekken_3_Recompiled.exe'
RELEASE=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
LOCK=json.loads((ROOT/'launcher/tools.lock.json').read_text())

class SetupError(Exception):
    pass

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def emit(event='status', **data):
    print(json.dumps({'event':event,**data}),flush=True)

def save_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)

def load_json(path):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def ready():
    state=load_json(STATE/'ready.json')
    if state.get('release')!=RELEASE or not EXE.is_file():return False
    if not (ROOT/'disc/Tekken 3 (USA).cue').is_file():return False
    try:
        if digest(EXE)!=state.get('exe_sha256'):return False
        if state.get('jun') and not jun_ready(BUILD/'mods/jun'):return False
    except OSError:return False
    return True

def jun_ready(folder):
    expected=load_json(ROOT/'tools/data/jun_runtime_hashes.json')
    return bool(expected) and all((folder/name).is_file() and digest(folder/name)==value for name,value in expected.items())

def log_line(text):
    STATE.mkdir(exist_ok=True)
    with (STATE/'setup.log').open('a',encoding='utf-8') as f:f.write(text+'\n')

def run(command, *, environment=None, directory=ROOT, friendly='Setup could not finish.', timeout=None):
    log_line('RUN '+subprocess.list2cmdline([str(x) for x in command]))
    with subprocess.Popen([str(x) for x in command],cwd=directory,env=environment,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0) as process:
        # The launcher's Windows Job owns this worker and all its children.
        last=0
        for line in process.stdout:
            log_line(line.rstrip())
            match=re.match(r'\[(\d+)/(\d+)\]',line)
            if match and time.monotonic()-last>.25:
                emit(detail='Preparing game files: '+match[1]+' / '+match[2]);last=time.monotonic()
        code=process.wait(timeout=timeout)
    if code:raise SetupError(friendly)

def download(spec):
    cache=STATE/'downloads';cache.mkdir(parents=True,exist_ok=True)
    path=cache/spec['filename']
    if path.is_file() and digest(path)==spec['sha256']:return path
    temp=path.with_suffix(path.suffix+'.part')
    request=urllib.request.Request(spec['url'],headers={'User-Agent':'Tekken3-Easy-Setup/'+RELEASE})
    try:
        with urllib.request.urlopen(request,timeout=60) as response,temp.open('wb') as out:
            total=int(response.headers.get('Content-Length',spec['size']));received=0;last=0
            h=hashlib.sha256()
            while True:
                block=response.read(1024*1024)
                if not block:break
                out.write(block);h.update(block);received+=len(block)
                if received>spec['size']:raise SetupError('A tool download has an unexpected size. Please retry.')
                if time.monotonic()-last>.25:
                    emit(detail=f'{received/1048576:.0f} / {total/1048576:.0f} MB downloaded');last=time.monotonic()
    except (OSError,urllib.error.URLError) as error:
        log_line(str(error));raise SetupError('The download was interrupted. Check your connection and click Try again.') from error
    if received!=spec['size'] or h.hexdigest()!=spec['sha256']:
        raise SetupError('A downloaded tool failed its integrity check. Click Try again to download it again.')
    temp.replace(path)
    return path

def safe_extract(archive,destination):
    destination=destination.resolve();destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        seen=set();total=0
        for info in z.infolist():
            name=info.filename.replace('\\','/')
            relative=Path(name);windows=PureWindowsPath(name)
            target=(destination/relative).resolve()
            total+=info.file_size
            if (windows.drive or relative.is_absolute() or '..' in relative.parts or ':' in name
                or destination not in target.parents or name.casefold() in seen
                or (info.external_attr>>16)&0o170000==0o120000 or total>3*1024**3):
                raise SetupError('An unsafe tool archive was rejected.')
            seen.add(name.casefold())
        for info in z.infolist():
            target=destination/info.filename.replace('\\','/')
            if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as source,target.open('wb') as out:shutil.copyfileobj(source,out)

def tools():
    folder=STATE/'tools/toolchain-1.0.10'
    marker=folder/'.ready.json'
    if (load_json(marker).get('archive_sha256')!=LOCK['toolchain']['sha256']
        or not all((folder/'bin'/name).is_file() for name in ('cmake.exe','clang.exe','clang++.exe','ninja.exe'))):
        emit(message='Getting the setup tools',detail='This only happens the first time.')
        archive=download(LOCK['toolchain'])
        emit(message='Unpacking the setup tools',detail='No system installation is needed.')
        safe_extract(archive,folder)
        if not (folder/'bin/cmake.exe').is_file():raise SetupError('The downloaded tools could not be prepared.')
        save_json(marker,{'archive_sha256':LOCK['toolchain']['sha256']})
    return folder

def mame():
    folder=STATE/'tools/mame-0.289';marker=folder/'.ready.json'
    if load_json(marker).get('archive_sha256')!=LOCK['mame']['sha256'] or not (folder/'mame.exe').is_file():
        emit(message="Getting Jun's import tool",detail='Downloading from the MAME project.')
        archive=download(LOCK['mame'])
        folder.mkdir(parents=True,exist_ok=True)
        emit(message="Preparing Jun's import tool",detail='Your game files stay on this PC.')
        run([archive,'-y','-o'+str(folder)],friendly='The Jun import tool could not be unpacked.')
        if not (folder/'mame.exe').is_file():raise SetupError('The Jun import tool is missing after unpacking.')
        save_json(marker,{'archive_sha256':LOCK['mame']['sha256']})
    return folder/'mame.exe'

def prepare_textures():
    from PIL import Image
    emit(message='Preparing the included mods',detail='Skins, outfit gallery and HD stage textures.')
    for record in load_json(ROOT/'tools/data/texture_payloads.json'):
        target=ROOT/record['path'];png=target.with_suffix('.png')
        if target.is_file() and digest(target)==record['sha256']:continue
        if digest(png)!=record['png_sha256']:raise SetupError('A bundled texture is damaged. Extract the download again.')
        with Image.open(png) as image:
            image=image.convert('RGBA')
            if record.get('crop'):image=image.crop(record['crop'])
            data=b'HDRGBA01'+struct.pack('<II',*image.size)+image.tobytes()
        if hashlib.sha256(data).hexdigest()!=record['sha256']:raise SetupError('A texture could not be prepared correctly.')
        temp=target.with_suffix('.tmp');temp.write_bytes(data);temp.replace(target)

def validate_files(disc,ttt,t3,include_jun):
    if not disc.is_file():raise SetupError('Choose your Tekken 3 USA PS1 disc image first.')
    emit(message='Checking your game files',detail='Checking the supported disc revision.')
    run([sys.executable,ROOT/'psxrecomp/psxrecomp_cli.py','verify-disc','--project-root',ROOT,'--config',ROOT/'game.toml','--disc',disc],
        friendly='This disc does not match the supported Tekken 3 USA (SLUS-00402) release. Choose its CUE or BIN file, with all tracks present.')
    if include_jun:
        if not ttt.is_file() or not t3.is_file():raise SetupError("Choose both arcade ZIPs for Jun, or turn off Include Jun Kazama.")
        sys.path.insert(0,str(ROOT/'tools'))
        import arcade_model_probe as probe
        definitions=load_json(probe.MANIFEST)['sets']
        try:
            for path,name in ((ttt,'tektagt'),(t3,'tekken3')):probe.reconstruct(path,definitions[name])
        except (ValueError,zipfile.BadZipFile,OSError) as error:
            log_line(str(error));raise SetupError('An arcade ZIP does not match the supported set. Jun needs tektagt (World C1) and tekken3 (World E1), in non-merged ZIPs.') from error

def build_game(toolchain,env,include_jun):
    cmake=toolchain/'bin/cmake.exe'
    emit(message='Preparing the game to build',detail='First setup can take several minutes.')
    # Setup explicitly configures on every attempt, after generation/import.
    # Skip Ninja's automatic regeneration checks: future-dated archive inputs
    # otherwise keep build.ninja dirty even after 100 successful regenerations.
    # This is local to Easy Setup; ordinary source builds keep their defaults.
    args=[cmake,'-S',ROOT,'-B',BUILD,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
          '-DCMAKE_SUPPRESS_REGENERATION=ON',
          '-DCMAKE_C_COMPILER='+str(toolchain/'bin/clang.exe'),'-DCMAKE_CXX_COMPILER='+str(toolchain/'bin/clang++.exe'),
          '-DCMAKE_MAKE_PROGRAM='+str(toolchain/'bin/ninja.exe'),'-DPython3_EXECUTABLE='+sys.executable,
          '-DPSX_STATIC_RUNTIME=ON','-DPSX_DEBUG_TOOLS=OFF','-DPSX_DEBUG_SERVER_LITE=OFF','-DPSX_NETPLAY=OFF',
          '-DPSXRECOMP_BIOS_STEMS=OpenBIOS','-DPSXRECOMP_FORCE_SETUP_HOST=OFF','-DPSXRECOMP_REQUIRE_GAME_C=ON',
          '-DTEKKEN3_BUILD_PC_PORT=OFF','-DTEKKEN3_JUN_EXPERIMENTAL='+('ON' if include_jun else 'OFF')]
    run(args,environment=env,friendly='The build tools could not finish setup. Open the setup log for details, then click Try again.')
    emit(message='Building your game',detail='This is the long part. Next time you can play immediately.')
    run([cmake,'--build',BUILD,'--target','psx-runtime','--parallel',env['CMAKE_BUILD_PARALLEL_LEVEL']],
        environment=env,friendly='The game build stopped. Open the setup log for the specific error, then click Try again. Completed work is kept.')

def prepare(disc,ttt,t3,include_jun):
    STATE.mkdir(exist_ok=True)
    with (STATE/'setup.log').open('w',encoding='utf-8') as f:f.write('Tekken 3 easy setup '+RELEASE+'\n')
    # Only run in the unpacked writable application folder, never require admin.
    if shutil.disk_usage(ROOT).free<4*1024**3:raise SetupError('Setup needs at least 4 GB of free space in this folder.')
    validate_files(disc,ttt,t3,include_jun)
    save_json(STATE/'last-inputs.json',{'disc':str(disc),'ttt1':str(ttt) if include_jun else '',
        't3_arcade':str(t3) if include_jun else '', 'jun':include_jun})
    toolchain=tools()
    env=dict(os.environ)
    # Keep compiler setup local to this process; do not modify the user's PATH.
    env['PATH']=str(toolchain/'bin')+os.pathsep+env.get('PATH','')
    env.update(PSXRECOMP_TOOLCHAIN_DIR=str(toolchain),RETCOMM_TOOLCHAIN_DIR=str(toolchain),
               PYTHONUTF8='1',PYTHONNOUSERSITE='1',CMAKE_BUILD_PARALLEL_LEVEL=str(min(8,max(2,os.cpu_count() or 2))))
    emit(message='Preparing your Tekken 3 disc',detail='Generating the game locally. Your files are not uploaded.')
    run([sys.executable,ROOT/'psxrecomp/psxrecomp_cli.py','generate','--project-root',ROOT,
         '--config',ROOT/'game.toml','--disc',disc,'--no-toolchain-download'],environment=env,
        friendly='The game files could not be prepared. Open the setup log for details, then click Try again.')
    prepare_textures()
    if include_jun and not jun_ready(ROOT/'workspace/jun-import/jun'):
        oracle=mame()
        emit(message='Adding Jun Kazama',detail='Importing her model, moves, voices and portraits. This runs muted.')
        run([sys.executable,ROOT/'tools/import_jun.py','--ttt1',ttt,'--t3-arcade',t3,'--mame',oracle,'--no-rebuild'],
            environment=env,friendly="Jun's import could not finish. Open the setup log for details, then click Try again.")
    build_game(toolchain,env,include_jun)
    if not EXE.is_file():raise SetupError('The game executable was not created.')
    if include_jun and not jun_ready(BUILD/'mods/jun'):raise SetupError('Jun is missing from the finished build. Click Try again.')
    save_json(STATE/'ready.json',{'release':RELEASE,'jun':include_jun,'exe_sha256':digest(EXE)})
    emit('complete',message='Ready to play',detail='Setup is complete.')

def launch_game(settings=False):
    if not ready():raise SetupError('Complete first setup before playing.')
    subprocess.Popen([str(EXE),'--launcher','--game',str(ROOT/'game.toml'),
        '--disc',str(ROOT/'disc/Tekken 3 (USA).cue')],cwd=ROOT)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--disc',required=True,type=Path)
    parser.add_argument('--ttt1',type=Path,default=Path())
    parser.add_argument('--t3-arcade',type=Path,default=Path())
    parser.add_argument('--no-jun',action='store_true')
    parser.add_argument('--wait-for-parent',action='store_true')
    args=parser.parse_args()
    # Parent assigns the process to a Job before releasing this handshake.
    if args.wait_for_parent and sys.stdin.readline().strip()!='START':sys.exit(1)
    try:prepare(args.disc.resolve(),args.ttt1.resolve(),args.t3_arcade.resolve(),not args.no_jun)
    except Exception as error:
        import traceback
        log_line(traceback.format_exc())
        emit('error',message=str(error) if isinstance(error,SetupError) else 'Setup stopped unexpectedly. Open the setup log for details, then click Try again.')
        sys.exit(1)

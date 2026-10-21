"""Read-only disassembly of archived selector overlay bytes, without booting."""
import base64,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'psxrecomp/tools'))
from disasm_helper import dis
start=int(sys.argv[1],16);end=int(sys.argv[2],16)
rows=json.loads((ROOT/'workspace/overlay-coverage-final/overlay_captures.json').read_text())
for row in rows:
    base=int(row['load_addr'],16);data=base64.b64decode(row['bytes_b64'])
    if base<=start and end<=base+len(data):
        for pc in range(start,end,4):
            w=struct.unpack_from('<I',data,pc-base)[0]
            print(f'{pc:08x}: {w:08x} {dis(pc,w)}')
        break
else:
    exe=(ROOT/'disc/SLUS_004.02').read_bytes()
    base=struct.unpack_from('<I',exe,0x18)[0];data=exe[0x800:]
    if not base<=start<end<=base+len(data):raise SystemExit('No archived bytes cover range')
    for pc in range(start,end,4):
        w=struct.unpack_from('<I',data,pc-base)[0]
        print(f'{pc:08x}: {w:08x} {dis(pc,w)}')

"""Check the native menu fingerprints and linked dispatch hook without booting."""
import base64
import json
import struct
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
captures = json.loads((root/'workspace/overlay-coverage-final/overlay_captures.json').read_text())
expected = {
    0x800db5b4: 0x27bdffa0,
    0x800db5cc: 0x24577f38,
    0x800db5d0: 0x3c02800f,
    0x800db5d8: 0x2456bfb8,
    0x800db7dc: 0x2d02000a,
    0x800db9f0: 0x90440014,
}
for address, instruction in expected.items():
    matches = [r for r in captures if int(r['load_addr'], 16) <= address < int(r['load_addr'], 16)+r['size']]
    assert any(struct.unpack_from('<I', base64.b64decode(r['bytes_b64']), address-int(r['load_addr'],16))[0] == instruction for r in matches), hex(address)

exe = root/'build-release/Tekken_3_Recompiled.exe'
nm = root.parent/'.tools/toolchain-v1.0.10/bin/llvm-nm.exe'
symbols = subprocess.check_output([str(nm), str(exe)], text=True)
hook = next(int(line.split()[0],16) for line in symbols.splitlines() if line.endswith(' __wrap_func_80028CD4'))
data = exe.read_bytes()
# PsxGameDispatchEntry: addr, resume_pc, range_index, range_count, function ptr.
entry = struct.pack('<IIIIQ', 0x80028cd4, 0, 9, 1, hook)
assert entry in data, 'Native screen dispatch does not point at the Quit hook'
print('PASS: archived overlay fingerprints and release dispatch-table hook')

"""Read-only selector diagnostics; never sends input or writes process memory.

Usage: python tools/inspect_live_selector.py PID MODULE_BASE
MODULE_BASE is the running executable's load address (decimal or 0x hex).
"""
import ctypes
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
exe = ROOT / 'build-release/Tekken_3_Recompiled.exe'
nm = ROOT.parent / '.tools/toolchain-v1.0.10/bin/llvm-nm.exe'
symbols = {}
for line in subprocess.check_output([str(nm), str(exe)], text=True).splitlines():
    parts = line.split()
    if len(parts) == 3:
        symbols[parts[2]] = int(parts[0], 16)
pe = exe.read_bytes()
pe_offset = struct.unpack_from('<I', pe, 0x3c)[0]
image_base = struct.unpack_from('<Q', pe, pe_offset + 24 + 24)[0]
slide = int(sys.argv[2], 0) - image_base
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
kernel.ReadProcessMemory.restype = ctypes.c_int
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
handle = kernel.OpenProcess(0x0010, False, int(sys.argv[1]))  # VM_READ only.
if not handle:
    raise ctypes.WinError(ctypes.get_last_error())

def read(address, length):
    buffer = ctypes.create_string_buffer(length)
    count = ctypes.c_size_t()
    if not kernel.ReadProcessMemory(handle, address, buffer, length, ctypes.byref(count)):
        raise ctypes.WinError(ctypes.get_last_error())
    assert count.value == length
    return buffer.raw

try:
    ram_pointer = struct.unpack('<Q', read(symbols['g_psx_ram'] + slide, 8))[0]
    ram = read(ram_pointer, 0x200000)
    def word(a): return struct.unpack_from('<I', ram, a & 0x1fffff)[0]
    def half(a): return struct.unpack_from('<H', ram, a & 0x1fffff)[0]
    if word(0x800ae204) == 10:
        op=word(0x80052e24)
        table=(op & 65535)<<16 if op>>16 == 0x3c03 else 0x80022768
        data=read(symbols['mod_memory']+slide+(table & 0xffffff),144) if table>=0x9f000000 else ram[table & 0x1fffff:(table & 0x1fffff)+144]
        print(json.dumps(dict(screen=10, phase=half(0x800ae224), table=hex(table),
                              patches={hex(a):hex(word(a)) for a in (0x8005427c,0x8005428c,0x80054414,0x80054424,0x8005449c,0x800544ac,0x80054840,0x80054858,0x80054d10,0x80054d78,0x80054da8)},
                              team_panels=[struct.unpack_from('<43I',ram,0xb8d70+p*0xac) for p in range(2)],
                              team_cells=[struct.unpack_from('<3H',data,i*6) for i in range(24)]),indent=2))
        sys.exit(0)
    cells = [struct.unpack_from('<6B3h', ram, 0x1296c8+i*12) for i in range(22)]
    panels = []
    for p in range(2):
        a = 0x8011864c+p*0x7c
        cursor = word(a+4)
        panels.append(dict(player=p+1, phase=word(a), cursor=cursor,
                           cell=cells[cursor] if cursor < len(cells) else None,
                           portrait=word(a+0x14), target=word(a+0x1c),
                           costume=word(a+0x20), name=word(a+0x28),
                           name_width=word(a+0x2c), saved=word(a+0x3c),
                           portrait_x=half(a+0x58), portrait_y=half(a+0x5a),
                           clut=half(a+0x5c), label_offset=half(a+0x7a)))
    print(json.dumps(dict(screen=word(0x800ae204), phase=half(0x800ae224),
                          frames=word(0x80118630), panels=panels,
                          cells=cells), indent=2))
finally:
    kernel.CloseHandle(handle)

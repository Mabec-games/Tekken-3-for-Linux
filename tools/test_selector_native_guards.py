"""Exercise the real RAM/native guard on selector code, without running the game."""
import argparse
import re
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--cc', default=str(ROOT.parent / '.tools/toolchain-v1.0.10/bin/clang.exe'))
    args = parser.parse_args()
    memory = (ROOT / 'psxrecomp/runtime/src/memory.c').read_text(encoding='utf-8')
    begin = memory.index('static int text_continuation_may_revisit(')
    end = memory.index('\n/* Preserve the generated-code ABI', begin)
    guard = memory[begin:end]
    exe = (ROOT / 'disc/SLUS_004.02').read_bytes()
    base = struct.unpack_from('<I', exe, 0x18)[0]
    cases = [
        # function, end, continuation after a draw call, changed grid lookup
        (0x80054194, 0x80054380, 0x8005431c, 0x8005428c),  # avatar
        (0x80054380, 0x80054694, 0x80054650, 0x80054424),  # cursor
        (0x80054d00, 0x80054f14, 0x80054df8, 0x80054d78),  # roster highlight
    ]
    preamble = '''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
static uint8_t ram[0x200000], reference[0x200000];
static uint8_t *text_ref_image=reference;
static uint32_t text_ref_lo=0, text_ref_hi=sizeof reference;
static uint64_t g_text_native_blocked,g_text_exact_mismatches;
static uint32_t g_text_exact_last_range_lo,g_text_exact_last_range_len;
static uint32_t g_text_exact_last_mismatch,g_text_exact_last_live,g_text_exact_last_ref;
'''
    tests = ['int main(void) {']
    for i, (lo, hi, resume, patch) in enumerate(cases):
        data = exe[0x800+lo-base:0x800+hi-base]
        assert len(data) == hi-lo
        words = struct.unpack('<' + 'I'*(len(data)//4), data)
        tests += [
            '{', f'uint32_t code[]={{ {",".join(hex(w) for w in words)} }};',
            f'uint32_t ranges[]={{ {lo:#x}u, sizeof code }};',
            f'memcpy(reference+{lo & 0x1fffff:#x},code,sizeof code);',
            'memcpy(ram,reference,sizeof ram);',
            f'assert(dirty_ram_text_native_ok_ranges_from(ranges,1,{resume:#x}u));',
            f'memset(ram+{patch & 0x1fffff:#x},0,4);',
            f'assert(!dirty_ram_text_native_ok_ranges_from(ranges,1,{resume:#x}u));',
            '}',
        ]
    tests += ['''
    /* A patched prologue with a genuinely straight tail remains native-safe. */
    memset(reference,0,sizeof reference);memset(ram,0,sizeof ram);
    uint32_t ranges[]={0x80001000,32,0x80001040,16};
    ram[0x1000]=1;
    assert(dirty_ram_text_native_ok_ranges_from(ranges,2,0x80001010));
    /* Backedges through a second instruction range cannot skip the patch. */
    uint32_t back=0x1000ffed; /* target 0x1000 from 0x1048 */
    memcpy(reference+0x1048,&back,4);memcpy(ram+0x1048,&back,4);
    assert(!dirty_ram_text_native_ok_ranges_from(ranges,2,0x80001010));
    uint32_t jump=0x08000400; /* j 0x1000 */
    memcpy(reference+0x1048,&jump,4);memcpy(ram+0x1048,&jump,4);
    assert(!dirty_ram_text_native_ok_ranges_from(ranges,2,0x80001010));
    jump=0x00400008; /* jr v0: conservatively retain interpretation */
    memcpy(reference+0x1048,&jump,4);memcpy(ram+0x1048,&jump,4);
    assert(!dirty_ram_text_native_ok_ranges_from(ranges,2,0x80001010));
    jump=0x03e00008; /* jr ra is a return, not a local backedge */
    memcpy(reference+0x1048,&jump,4);memcpy(ram+0x1048,&jump,4);
    assert(dirty_ram_text_native_ok_ranges_from(ranges,2,0x80001010));
    ram[0x1014]=1;
    assert(!dirty_ram_text_native_ok_ranges_from(ranges,2,0x80001010));
    memcpy(ram,reference,sizeof ram);ram[0x1030]=1; /* non-code gap */
    assert(dirty_ram_text_native_ok_ranges_from(ranges,2,0));
    assert(!dirty_ram_text_native_ok_ranges_from(ranges,2,0x80002000));
    puts("PASS: actual selector P2 backedges, straight tails, jumps and code gaps");
    return 0;
}
''']
    source = preamble + guard + '\n' + '\n'.join(tests)
    with tempfile.TemporaryDirectory(prefix='selector-guard-') as temp:
        path = Path(temp)
        (path / 'test.c').write_text(source)
        subprocess.run([args.cc, '-std=c11', '-Wall', '-Wextra', str(path / 'test.c'),
                        '-o', str(path / 'test.exe')], check=True)
        subprocess.run([str(path / 'test.exe')], check=True)
        # Prove these cases catch the previous guard, not just the new behavior.
        old = re.sub(r'if \(changed_prefix && text_continuation_may_revisit\(lo_len_pairs, count, at\)\)',
                     'if (0)', source)
        (path / 'old.c').write_text(old)
        subprocess.run([args.cc, '-std=c11', str(path / 'old.c'), '-o', str(path / 'old.exe')], check=True)
        result = subprocess.run([str(path / 'old.exe')], capture_output=True, text=True)
        assert result.returncode != 0, 'Regression did not fail with the previous clipping behavior'
        print('PASS: previous clipped guard reproduces the P2 regression')


if __name__ == '__main__':
    main()

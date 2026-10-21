#!/usr/bin/env python3
"""Extract Jun's twelve original arcade voice samples from verified local ROMs.

The character table is read from the original game, not inferred from sample
order. C352 mu-law and interpolation follow MAME's BSD-3-Clause implementation
by R. Belmont and superctr (commit aab5dcadb6025303ba019d0189344a5df536a623):
https://github.com/mamedev/mame/blob/aab5dcadb6025303ba019d0189344a5df536a623/src/devices/sound/c352.cpp
The 0x18af frequency was verified by requesting all twelve IDs through the
original H8 driver and recording the C352 key-on registers.
"""
from pathlib import Path
import hashlib
import json
import struct
import wave

try:
    from .prepare_jun_import import verified, RAM_SHA
except ImportError:
    from prepare_jun_import import verified, RAM_SHA

WORK = Path(__file__).resolve().parents[1] / 'workspace/jun-import'
SUB_SHA = '5b5ffddf6df97be32919462c23a7d0896498bbf01af547566ff45449ae0811f8'
C352_SHA = 'cb68614775f792b6bf97149396a1cf12645802f8ec1b8da014554142e579f281'
FREQUENCY = 0x18af


def mulaw_table():
    positive = []
    level = 0
    for i in range(128):
        positive.append(level << 5)
        level += 1 if i < 16 else 2 if i < 24 else 4 if i < 48 else 8 if i < 100 else 16
    return positive + [-v - 32 for v in positive]


def decode_sample(rom, bank, start, end, flags, frequency=FREQUENCY):
    """Render a forward, one-shot C352 voice to 44100 Hz mono PCM.

    Crossing a 64 KiB bank boundary is legal (Jun damage sample 162 does it).
    The terminal byte silences the channel in the original C352. Simulate its
    88200 Hz interpolation clock, then average pairs for the host output rate.
    Gain/panning belong to the runtime mixer, not the extracted waveform.
    """
    if flags != 8 or not 1 <= frequency <= 65535:
        raise ValueError('Expected a forward, non-looping mu-law voice')
    count = ((end - start) & 65535) + 1
    address = bank * 65536 + start
    if address + count > len(rom):
        raise ValueError('Sample extends outside its ROM')
    table = mulaw_table()
    counter, sample, last, index = 65535, 0, 0, 0
    pcm, pair = [], []
    while index < count:
        next_counter = counter + frequency
        if next_counter & 65536:
            last, sample = sample, table[rom[address + index]]
            index += 1
            if index == count:
                sample = 0
        counter = next_counter & 65535
        pair.append(last + ((counter * (sample - last)) >> 16))
        if len(pair) == 2:
            pcm.append((pair[0] + pair[1]) // 2)
            pair.clear()
    # End without a discontinuity, including the chip's terminal sample.
    pcm.extend([0] * 32)
    return struct.pack('<' + 'h' * len(pcm), *pcm)


def build(work=WORK):
    ram = verified(work / 'jun-select-ram.bin', RAM_SHA)
    sub = verified(work / 'ttt1/sub.bin', SUB_SHA)
    rom = verified(work / 'ttt1/c352.bin', C352_SHA)
    # Actor +0x1c is Jun's sound profile 19; body ID 30 and moves key 28 differ.
    pointer = struct.unpack_from('<I', ram, 0x11e1c + 19 * 20)[0] & 0x3fffff
    groups = struct.unpack_from('<4H', ram, pointer)
    ids = struct.unpack_from('<12H', ram, pointer + 8)
    if groups != (7, 3, 1, 1) or ids != (*range(164, 171), 160, 161, 162, 163, 171):
        raise ValueError('Jun character voice table changed')
    roles = {v: (group + 2, index) for group, chunk in enumerate(
        (ids[:7], ids[7:10], ids[10:11], ids[11:])) for index, v in enumerate(chunk)}
    blob = bytearray(32 + 12 * 16)
    report = []
    directory = work / 'jun/voices'
    directory.mkdir(exist_ok=True)
    for i, sample_id in enumerate(range(160, 172)):
        bank, flags, start, end, pitch = struct.unpack_from('<5H', sub, 0x9436 + sample_id * 10)
        if pitch != 0x1280:
            raise ValueError('Arcade driver pitch no longer matches the oracle')
        pcm = decode_sample(rom, bank, start, end, flags)
        group, index = roles[sample_id]
        struct.pack_into('<4I', blob, 32 + i * 16, sample_id, len(blob), len(pcm) // 2, group << 16 | index)
        blob.extend(pcm)
        role = {2: 'attack', 3: 'damage', 4: 'ko', 5: 'victory'}[group]
        with wave.open(str(directory / f'{sample_id:03d}-{role}-{index + 1}.wav'), 'wb') as out:
            out.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
            out.writeframes(pcm)
        report.append(dict(id=sample_id, role=role, index=index, bank=bank, start=start,
                           end=end, flags=flags, driver_pitch=pitch, frequency=FREQUENCY,
                           frames=len(pcm)//2, pcm_sha256=hashlib.sha256(pcm).hexdigest()))
    struct.pack_into('<8I', blob, 0, 0x3156554a, 1, len(blob), 12, 44100, 0, 0, 0)
    target = work / 'jun/Jun-TTT1-voices.juv'
    target.write_bytes(blob)
    result = dict(format_version=1, sha256=hashlib.sha256(blob).hexdigest(), samples=report,
                  source_c352_sha256=C352_SHA, source_sub_sha256=SUB_SHA,
                  sound_profile=19, group_counts=groups, group_ids=ids)
    (work / 'jun/voice-report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(path=str(target), bytes=len(blob), samples=12, sha256=result['sha256'])))
    return result


if __name__ == '__main__':
    build()

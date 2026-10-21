"""System 12 -> SLUS-00402 combat data translations.

These are field translations, not a nearest-move/template selection. Addresses
refer to the verified private executable captures used by convert_jun_moves.
"""
import struct


def flags(value):
    # Native flags start at bit 8. TTT added a nine-direction posture flag at
    # bit 8 and a flag at bit 21; its translation/root flags moved to 19/20/22.
    low = (value & 0xff) | ((value & 0x7fe00) >> 1)
    return (low << 8) | ((value & 0x180000) << 9) | ((value & 0x400000) << 8)


def properties(ram, pointer):
    """Yield timed property rows, including damage during paired animations.

    Dispatches: TTT 800FBE88; PS1 800458C8. Unsupported tag operations are
    returned separately so the export audit does not hide them.
    """
    out, omitted = [], []
    if not pointer:
        return out, omitted
    for i in range(256):
        frame, op = struct.unpack_from('<HH', ram, (pointer & 0x3fffff)+i*4)
        if not frame:
            return out, omitted
        kind, arg = op >> 8, op & 255
        if kind==5:continue  # The original dispatch entry is a no-op.
        translated = {1:1, 2:2, 3:3, 4:4, 10:6, 11:7, 12:8,
                      13:9, 14:10, 24:11, 25:12, 26:13}.get(kind)
        if 0x1b <= kind < 0x4b:
            group, action = divmod(kind-0x1b, 16)
            if action < 8:
                translated = 0xe+group*16+action
        if kind==0x26:
            translated=0x40  # Jun facial expression, handled by her texture adapter.
        if translated is None:
            omitted.append((frame, kind, arg))
        else:
            out.append((frame, translated << 8 | arg))
    raise ValueError('Unterminated timed property list')


def sound_events(ram, pointer):
    """The two sound dispatchers share their three-halfword event format.

    Category 8 addresses a separate animation-event table, not a sound. It
    must be relocated by the event-table port and is reported independently.
    """
    out, animation_events = [], []
    if pointer:
        for i in range(3):
            event = struct.unpack_from('<H', ram, (pointer & 0x3fffff)+i*2)[0]
            if event == 0xffff:
                break
            if event >> 12 == 8:
                animation_events.append(event & 0xfff)
                out.append(0x8000 | (1024+(event&0xfff) if event&0xfff else 0))
            else:
                out.append(event)
    return out, animation_events


def event_script(ram, index):
    start=struct.unpack_from('<H',ram,0x1622c+index*2)[0]
    out=[]
    previous=0
    for k in range(256):
        frame,kind,value=struct.unpack_from('<BBH',ram,0x1213c+(start+k)*4)
        if not frame:return out+[0]
        if kind>3 or frame<previous:raise ValueError('Invalid timed sound script')
        out.append(frame | kind<<12 | value<<16);previous=frame
    raise ValueError('Unterminated timed sound script')


def reaction(ram, index):
    """Seven angle/pushback fields, followed by fourteen reaction aliases."""
    p = 0x19ff88 + index*56
    return struct.unpack_from('<7I14H', ram, p)


def transition(kind):
    # The PS1 inserts a reserved state before the paired throw states. Later
    # TTT tag states have no counterpart in a solo fight.
    value = kind & 127
    if value <= 30:
        return value | ((kind >> 8) & 0xc0)
    if value in (31,32):
        return 33 | ((kind >> 8) & 0xc0)
    if 33 <= value <= 35:
        # Source-only facing transitions, implemented by the combat adapter.
        return value+12 | ((kind >> 8) & 0xc0)
    if 36 <= value <= 46:
        return value-2 | ((kind >> 8) & 0xc0)
    return None


def native_aliases():
    """Engine entry points, compared in the two resolved alias tables.

    These are semantic alias ranges (walk, guard, getup, win), not animation
    similarity matches. Character attacks enter through the source graph.
    """
    result = {0:4, 1:5, 2:6, 3:56, 6:59, 21:61, 22:62,
              24:63, 26:64, 27:65, 28:65, 29:67,
              0x87:0xb9, 0x88:0xbe, 0xd58:0x1268,
              0xd61:0x128a, 0xd62:0x128d, 0xd63:0x128e,
              0xd64:0x128f, 0xd65:0x1290, 0xd66:0x1291,
              0xd6c:0x129c, 0xd6d:0x129d}
    for start,end,delta in (
        (30,33,38),(36,40,38),(44,49,38),(51,54,38),(56,70,38),
        (0x7f,0x86,0x36),(0x89,0xa6,0x36),(0xa7,0xc8,0x38),
        (0xd1,0xed,0x30),(0xf4,0x106,0x2e),(0x108,0x114,0x2f),
        (0x11b,0x122,0x2f),(0xd06,0xd56,0x511),
        (0xd59,0xd60,0x511),(0xd67,0xd6a,0x52b)):
        result.update({i:i+delta for i in range(start,end+1)})
    return result


def motion_groups(ram):
    """Original contact-exception groups and their PS1 group identities.

    TTT added an initial empty list and removed PS1's reserved group 15.
    The shared groups end at 46; the later tag-specific lists differ.
    """
    result={}
    offset=0
    for ordinal in range(47):
        start=offset;clips=[]
        while True:
            index=struct.unpack_from('<h',ram,0xec558+offset*2)[0];offset+=1
            if index<0:break
            clips.append(struct.unpack_from('<I',ram,0x36768+index*52)[0])
        if ordinal:
            result[start]=(ordinal-1 if ordinal<=15 else ordinal,sorted(set(clips)))
    return result

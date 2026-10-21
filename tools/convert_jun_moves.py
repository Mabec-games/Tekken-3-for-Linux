#!/usr/bin/env python3
"""Build the private, experimental Jun combat bridge from verified donor data.

Preserves donor motion, input links, hit-table damage, attacking bones and
active frames. Hit reactions use translated source tables. Unsupported
conditions/commands are reported and omitted, never silently treated as true.
"""
from pathlib import Path
import collections
import hashlib
import json
import struct
try:
    from .prepare_jun_import import BANK_SHA, RAM_SHA, verified
    from .ttt1_motion import decode
    from . import jun_solo_semantics as solo
except ImportError:
    from prepare_jun_import import BANK_SHA, RAM_SHA, verified
    from ttt1_motion import decode
    import jun_solo_semantics as solo

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'workspace/jun-import'
BASE_ID = 8192
NATIVE_EXE_SHA='fbda8b68e5799dbef4af39a161783bc670c15b0aa0e87dce65e210717da19b8c'
# Shared contact tests (2..23), distance, attack class, posture and reaction
# flags. TTT's inserted facing tests shift the later PS1 condition numbers.
CONDITIONS = {i:i for i in range(37)}
CONDITIONS.update({i:i-3 for i in range(40,72) if i!=50})
CONDITIONS.update({70:67,71:68})
CONDITIONS.update({i:i-0x1b for i in range(0x60,0x67)})
CONDITIONS.update({37:76,38:77,39:78})
CONDITIONS.update({i:79+(i-80)%4 for i in range(80,88)})


def character_requirement(code):
    if code in (0,0xed):return True
    if code==0xec:return False
    if 1<=code<0x22:return code-1==28
    if 0x22<=code<0x43:return code-0x22!=28
    if 0x85<=code<0xa7:return code-0x85==30
    if 0xc9<=code<0xeb:return code-0xc9!=30
    return None


def cancel_rows(ram,pointer,stack=()):
    if pointer in stack or len(stack)>8:raise ValueError('Recursive cancel list')
    for k in range(1024):
        row=struct.unpack_from('<7H',ram,(pointer&0x3fffff)+k*14)
        if row[0]==0x800e:return
        if row[0]==0x800d:
            yield from cancel_rows(ram,0x801b3740+row[3]*14,stack+(pointer,))
            continue
        yield row
        if row[0]==0x8000:return
    raise ValueError('Unterminated cancel list')


def hit_data(ram,index):
    """Resolve Jun's normal hit row as the arcade's 801012D4 does.

    Record +0x14 indexes ten-byte hit rows at 800EC8BC. Record +0x28
    contains four limb IDs, not damage. Opponent-specific rows are exported
    separately and resolved against the actual opponent by the adapter.
    """
    dynamic=False
    for i in range(128):
        row=struct.unpack_from('<5H',ram,0xec8bc+(index+i)*10)
        req=character_requirement(row[0])
        if row[0]==0xffff or req is True:return row,dynamic
        if req is None:dynamic=True
    raise ValueError('Unterminated arcade hit-data list')


def hit_rows(ram,index):
    rows=[]
    for k in range(128):
        row=struct.unpack_from('<5H',ram,0xec8bc+(index+k)*10)
        rows.append(row)
        if row[0]==0xffff:return rows
    raise ValueError('Unterminated arcade hit-data list')


def build(work=WORK):
    ram = verified(work/'jun-select-ram.bin', RAM_SHA)
    bank = verified(work/'ttt1/bankedroms.bin', BANK_SHA)
    manifest = json.loads((work/'jun/motion/manifest.json').read_text())
    native_exe = verified(ROOT/'disc/SLUS_004.02',NATIVE_EXE_SHA)[0x800:]
    aliases = struct.unpack_from('<5515I', ram, 0x2a7350)
    addresses = {x['address'] for x in manifest['records']}
    # Common locomotion supplies crouching, walking and turning for the donor.
    addresses.update(a for a in aliases[56:344] if a != 0x8009374c)
    native_aliases=solo.native_aliases()
    native_aliases={k:v for k,v in native_aliases.items() if aliases[v]!=0x8009374c}
    addresses.update(aliases[v] for v in native_aliases.values())
    # Follow the actual Jun graph, including moves shared with Jin. A diff of
    # their alias tables alone omits shared recovery and attack destinations.
    pending=list(addresses)
    while pending:
        v=struct.unpack_from('<13I',ram,pending.pop()&0x3fffff)
        targets=[v[4]&65535]
        for cmd,req,param,nxt,kind,window,end in cancel_rows(ram,v[3]):
            if cmd==0x8000 or (character_requirement(req&255) is True and not (cmd<0x8000 and cmd&0x4000) and
                (req>>8)&127 in CONDITIONS and solo.transition(kind) is not None and not kind&0x3f80):
                targets.append(nxt)
        for hit in hit_rows(ram,v[5]&65535):
            for reaction_id in (hit[2],hit[3]):
                if reaction_id:targets.extend(solo.reaction(ram,reaction_id)[7:])
        for target_alias in targets:
            if 0<=target_alias<len(aliases):
                address=aliases[target_alias]
                if address not in addresses:
                    addresses.add(address);pending.append(address)
    addresses = sorted(addresses)
    indices = {a:i for i,a in enumerate(addresses)}
    raw = [struct.unpack_from('<13I', ram, a & 0x3fffff) for a in addresses]
    skipped = collections.Counter()
    omitted_conditions = collections.Counter()
    patterns = {}
    groups=solo.motion_groups(ram)
    event_scripts={}
    rx_ids=sorted({idx for v in raw for row in hit_rows(ram,v[5]&65535) for idx in row[2:4]})
    dynamic_hits=[]
    distance_hits=[]
    # The native reaction table contains 633 records. Preserve stock fighters;
    # append source-derived Jun rows and their original pushback curves.
    rx_map={idx:633+i for i,idx in enumerate(rx_ids)}
    rx_blob=bytearray(native_exe[0xce8:0xce8+633*42])
    push_blob=bytearray(native_exe[0x75c:0xce8])
    push_offsets={}
    counter_blob=bytearray(native_exe[0x77dc:0x7c10])
    # Matching condition handlers were compared in the two executables.
    conditions=CONDITIONS

    def input_pattern(cmd):
        if cmd not in patterns:
            start=0x772+cmd*2
            words=[]
            for k in range(65):
                value=struct.unpack_from('<H',ram,start+k*2)[0]
                words.append(value)
                if k and not value:break
            else:raise ValueError('Unterminated input sequence')
            if not 1<=words[0]<=60 or len(words)<3:raise ValueError('Invalid input sequence')
            patterns[cmd]=(0xe000+len(patterns),words)
        return patterns[cmd][0]

    def target(alias):
        if alias == 56: return 3
        if 0 <= alias < len(aliases) and aliases[alias] in indices:
            return BASE_ID + indices[aliases[alias]]
        return None

    def required_target(alias):
        resolved=target(alias)
        if resolved is None:
            raise ValueError(f'Unconverted solo animation destination {alias:04x}')
        return resolved

    def cancels(pointer):
        for cmd,req,param,nxt,kind,window,end in cancel_rows(ram,pointer):
            dest = target(nxt)
            if cmd == 0x8000:
                # End-of-animation links also carry a transition and facing
                # flags. Forcing type 6 loses the half-turn on back-facing
                # recovery (for example alias C1 -> C2 uses source 800B).
                transition = solo.transition(kind)
                if transition is None or kind & 0x1f80:
                    raise ValueError(f'Unconverted recovery transition {kind:04x}')
                # Source bit 13 requests a partner swap at 800FF424. Solo
                # recovery keeps the actor and the base facing transition.
                if kind & 0x2000:skipped['solo_excluded_partner_recovery']+=1
                yield struct.pack('<4H4B',0xc000,0,0,required_target(nxt),transition,window>>8,end&255,end>>8)
                return
            requirement=character_requirement(req&255)
            if requirement is False:
                skipped['other_character_rule']+=1;continue
            if cmd<0x8000 and cmd&0x4000:
                skipped['solo_excluded_tag_input']+=1;continue
            if 0x64<=req&255<0x85 or 0xa7<=req&255<0xc9 or kind&0x3f80 or (req>>8)&127 in (88,89,90,91,92):
                skipped['solo_excluded_partner_transition']+=1;continue
            if (req>>8)&127==95:
                # TTT's round-defeat signal; the PS1 round controller enters
                # native D6C/D6D, mapped to these same Jun defeat motions.
                skipped['native_round_controller']+=1;continue
            # Bit 7 gates the opponent's tag state (800FE1B8..800FE238).
            # With no tag partner in PS1 combat that gate permits the normal
            # low-seven-bit condition; it is not a new condition number.
            condition=conditions.get((req>>8)&127)
            if requirement is None or condition is None:
                omitted_conditions[f'{req:04x}']+=1
                skipped['conditional_requirement'] += 1; continue
            if dest is None:
                skipped['unmapped_destination'] += 1; continue
            transition = solo.transition(kind)
            if transition is None or kind & 0x3f80:
                skipped['transition_type'] += 1; continue
            if cmd in (0x8001,0x8002):cmd+=0x4000
            elif cmd>=0x800f:cmd=input_pattern(cmd)
            elif cmd>=0x8000 or cmd&0x4000:
                skipped['special_input']+=1;continue
            if condition==74:
                param|=0x8000  # Source alias checked by the contact bridge.
            elif condition==75:
                if param not in groups:raise ValueError(f'Unknown contact group {param:x}')
                param|=0x4000
            # Bit 15/14 became bit 7/6 in the PS1 transition byte.
            yield struct.pack('<4H4B',cmd,condition<<8,param,dest,transition,window>>8,end&255,end>>8)

    # Header, metadata records (16 bytes), native records (56 bytes).
    blob = bytearray(32+len(raw)*72)
    relocs=[]
    pose_offsets={}
    def append(data):
        blob.extend(b'\0'*(-len(blob)%4)); offset=len(blob);blob.extend(data);return offset
    for i,v in enumerate(raw):
        source=v[0]
        if source not in pose_offsets:
            count=bank[source]
            data=struct.pack('<II',0x4a554e00|count,57)
            data+=b''.join(struct.pack('<57H',*decode(bank,source,f)) for f in range(count))
            pose_offsets[source]=append(data)
        converted=list(cancels(v[3]))
        # A nested group can end without the parent sentinel.
        if not converted or struct.unpack_from('<H',converted[-1])[0]!=0xc000:
            converted.append(struct.pack('<4H4B',0xc000,0,0,required_target(v[4]&65535),6,0,0,0))
        # Flattened subroutines return at 800e; only the outer list terminates.
        cp=append(b''.join(converted))
        hit,dynamic_hit=hit_data(ram,v[5]&65535)
        damage=hit[1]
        if hit[4]:distance_hits.append((i,hit[4],rx_map[hit[3]],rx_map[hit[2]]))
        if dynamic_hit:
            variants=hit_rows(ram,v[5]&65535)
            if any(not 0x43<=row[0]<0x64 or row[1:]!=variants[0][1:] for row in variants[:-1]) or any(
                variants[0][k]!=hit[k] for k in (1,3,4)):
                raise ValueError('Untranslated opponent-specific hit rule')
            mask=sum(1<<(row[0]-0x43) for row in variants[:-1])
            dynamic_hits.append((i,mask,rx_map[variants[0][2]],rx_map[hit[2]]))
        t=[0]*14
        t[0]=pose_offsets[source];t[1]=v[1];t[2]=v[2];t[3]=cp
        # Both engines add the high halfword to facing at recovery.
        t[4]=(v[4]&0xffff0000)|required_target(v[4]&65535)
        # Only the low halfword changes from hit-row index to damage. The
        # signed upper halfword is horizontal movement during the airborne
        # frame window; dropping it turns forward/back jumps into verticals.
        t[5]=(v[5]&0xffff0000)|damage
        t[6]=(v[6]&0xffffff00)|bank[source]
        sounds,animation_events=solo.sound_events(ram,v[7])
        for event in animation_events:
            if event:event_scripts[1024+event]=solo.event_script(ram,event)
        t[7]=append(struct.pack(f'<{len(sounds)+1}H',*sounds,0xffff))
        props,omitted_props=solo.properties(ram,v[8])
        t[8]=append(b''.join(struct.pack('<HH',*p) for p in props)+b'\0'*4)
        for _,kind,_ in omitted_props:skipped[f'timed_property_{kind:02x}']+=1
        t[9]=solo.flags(v[9])
        # v3 packs store these IDs directly; the runtime allocates the native
        # descriptor and evaluates the sweep from Jun's animated skeleton.
        t[10]=v[10]
        t[11]=((v[11]&0xffff)<<8)|((v[11]>>16)&255)
        t[12]=(v[12]&65535)|(rx_map[hit[2]]<<16)
        t[13]=len(counter_blob)//4
        # TTT 800FB378..800FB3D0 uses hit[3] only inside hit[4] distance.
        # The native distance table has the same (reaction, threshold) pair.
        # Both its selector and its range-test base must be relocated.
        counter_blob.extend(struct.pack('<HH',rx_map[hit[3]] if hit[4] else rx_map[hit[2]],hit[4]))
        rp=32+len(raw)*16+i*56
        struct.pack_into('<14I',blob,rp,*t)
        relocs.extend((rp,rp+12,rp+28,rp+32))
        struct.pack_into('<4I',blob,32+i*16,source,addresses[i],rp,len(converted))
    reloc_offset=append(struct.pack(f'<{len(relocs)}I',*relocs))
    sequence_data=struct.pack('<I',len(patterns))
    for command,words in patterns.values():
        sequence_data+=struct.pack('<HH',command,len(words))+struct.pack(f'<{len(words)}H',*words)
    blob.extend(sequence_data)
    neutral=indices[aliases[56]]
    struct.pack_into('<8I',blob,0,0x314d554a,4,len(blob),len(raw),neutral,reloc_offset,len(relocs),32+len(raw)*16)
    for idx in rx_ids:
        r=solo.reaction(ram,idx)
        fields=[]
        for k,value in enumerate(r[:7]):
            if k in (1,3,5,6) and value:
                if value not in push_offsets:
                    push_offsets[value]=len(push_blob)//2
                    push_blob.extend(ram[value&0x3fffff:(value&0x3fffff)+20])
                value=push_offsets[value]
            fields.append(value&65535)
        rx_blob.extend(struct.pack('<21H',*(required_target(a) for a in r[7:]),*fields))
    tables=bytearray(32)+rx_blob+push_blob+counter_blob
    def chunk(name,payload):
        tables.extend(name+struct.pack('<I',len(payload))+payload)
    chunk(b'ALIA',b''.join(struct.pack('<HH',native,target(source)) for native,source in sorted(native_aliases.items())))
    chunk(b'SRCA',struct.pack('<5515I',*aliases))
    chunk(b'GRUP',b''.join(struct.pack('<HHI',source,native,len(clips))+struct.pack(f'<{len(clips)}I',*clips)
                         for source,(native,clips) in sorted(groups.items())))
    chunk(b'EVNT',b''.join(struct.pack('<II',i,len(events))+struct.pack(f'<{len(events)}I',*events)
                         for i,events in sorted(event_scripts.items())))
    chunk(b'DYNH',b''.join(struct.pack('<4I',*row) for row in dynamic_hits))
    struct.pack_into('<8I',tables,0,0x3154534a,2,len(tables),len(rx_blob)//42,len(push_blob),len(counter_blob)//4,0,0)
    allowed_exclusions={'other_character_rule','native_round_controller',
                        'solo_excluded_tag_input','solo_excluded_partner_transition',
                        'solo_excluded_partner_recovery'}
    unresolved={kind:n for kind,n in skipped.items() if kind not in allowed_exclusions}
    if unresolved or omitted_conditions:
        raise ValueError(f'Incomplete solo conversion: {unresolved}, conditions {dict(omitted_conditions)}')
    (work/'jun/Jun-TTT1-tables.jst').write_bytes(tables)
    output=work/'jun/Jun-TTT1-combat.jmv';output.write_bytes(blob)
    report=dict(records=len(raw),clips=len(pose_offsets),cancel_entries=sum(struct.unpack_from('<I',blob,32+i*16+12)[0] for i in range(len(raw))),
                input_sequences=len(patterns),omitted_rules=dict(skipped),omitted_conditions=dict(omitted_conditions.most_common()),sha256=hashlib.sha256(blob).hexdigest(),
                status='Solo source graph converted',
                animation_event_scripts=len(event_scripts),opponent_specific_hit_records=len(dynamic_hits),
                distance_specific_hit_records=len(distance_hits),
                native_entry_points=len(native_aliases),native_fallback_templates=[],
                source_default_reaction='8009374c' if 0x8009374c in indices else None,
                unresolved=[],validation_report='../joint-validation.json',
                limits=['Native fight camera replaces TTT1 camera scripts',
                        'Hair and bow retain rigid attachment, without secondary physics',
                        'Live fixtures sample commands and opponents; exhaustive timing parity is not established'])
    (work/'jun/combat-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__': build()

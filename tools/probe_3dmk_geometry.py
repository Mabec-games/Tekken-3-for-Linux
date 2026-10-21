"""Inspect Tekken 3 arcade 3DMK vertex and indexed-face records."""
import argparse
from pathlib import Path
import struct


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def parse(data):
    rows = u32(data, 0)
    if data[8:12] != b'3DMK' or rows > 256:
        raise ValueError('Not a supported 3DMK header')
    output = []
    for row in range(rows):
        fields = struct.unpack_from('<14I', data, 24 + row * 56)
        vertex_ptr, face_ptr, uv_ptr = fields[:3]
        if any(p + 4 > len(data) for p in (vertex_ptr, face_ptr, uv_ptr)):
            raise ValueError(f'row {row}: pointer outside slice')
        vertex_count = u32(data, vertex_ptr)
        if vertex_count > 4096 or vertex_ptr + 4 + vertex_count * 8 > len(data):
            raise ValueError(f'row {row}: invalid vertex stream')
        vertices = [struct.unpack_from('<3h', data, vertex_ptr + 4 + j * 8)
                    for j in range(vertex_count)]
        faces = []
        face_words = []
        group_counts = []
        fp, up = face_ptr, uv_ptr
        for group in range(4):
            count = u32(data, fp)
            uv_count = u32(data, up)
            if count != uv_count or count > 4096:
                raise ValueError(f'row {row}, group {group}: paired counts differ: {count}/{uv_count}')
            group_counts.append(count)
            fp += 4
            up += 4
            for _ in range(count):
                if fp + 8 > len(data) or up + 12 > len(data):
                    raise ValueError(f'row {row}: truncated face stream')
                indices = tuple(data[fp + j] for j in range(4 if group & 1 else 3))
                faces.append(indices)
                face_words.append(u32(data, fp + 4))
                fp += 8
                up += 12
        output.append(dict(row=row, fields=fields, vertices=vertices,
                           faces=faces, face_words=face_words, groups=group_counts,
                           face_end=fp, uv_end=up))
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    for mesh in parse(args.path.read_bytes()):
        vertices = mesh['vertices']
        bounds = tuple((min(v[i] for v in vertices), max(v[i] for v in vertices))
                       for i in range(3)) if vertices else None
        print('row', mesh['row'], 'vertices', len(vertices), 'faces', len(mesh['faces']),
              'groups', mesh['groups'], 'bounds', bounds,
              'max_index', max((max(f) for f in mesh['faces']), default=None),
              'face_word_range', (min(mesh['face_words']), max(mesh['face_words'])) if mesh['face_words'] else None,
              'end', hex(mesh['face_end']), hex(mesh['uv_end']))


if __name__ == '__main__':
    main()

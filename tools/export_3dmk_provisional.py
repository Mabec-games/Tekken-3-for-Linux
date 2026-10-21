"""Export verified coordinate samples from a 3DMK row as a point cloud.

The face-stream indices are not yet proven to map directly to these positions;
therefore this tool does not create a mesh or suggest polygon connectivity.
"""
import argparse
from pathlib import Path
import struct

from PIL import Image, ImageDraw
from probe_3dmk_geometry import parse, u32


def positions(data, mesh):
    pointer = mesh['fields'][12]
    if not pointer:
        return []
    count = u32(data, pointer)
    if count > 4096 or pointer + 4 + count * 8 > len(data):
        raise ValueError('invalid position stream')
    return [struct.unpack_from('<3h', data, pointer + 4 + i * 8)
            for i in range(count)]


def export(data, mesh, target):
    verts = positions(data, mesh)
    if not verts:
        raise ValueError('row has no coordinate samples')

    target.mkdir(parents=True, exist_ok=True)
    obj = target / f'arcade-3dmk-row-{mesh["row"]:02}-pointcloud.obj'
    obj.write_text('\n'.join([
        '# Verified coordinate stream; polygon connectivity not decoded.',
        '# This is not a complete or identified character model.',
        f'o arcade_3dmk_row_{mesh["row"]:02}',
        *[f'v {x} {y} {z}' for x, y, z in verts],
        *[f'p {i + 1}' for i in range(len(verts))],
        '',
    ]), encoding='ascii')

    width, height, margin = 1100, 760, 55
    image = Image.new('RGB', (width, height), (15, 19, 25))
    draw = ImageDraw.Draw(image)
    views = [
        ('FRONT  X/Y', [(x, y) for x, y, z in verts]),
        ('SIDE  Z/Y', [(z, y) for x, y, z in verts]),
        ('TOP  X/Z', [(x, z) for x, y, z in verts]),
    ]
    for view_index, (label, projected) in enumerate(views):
        box_x = 30 + view_index * 360
        box_y = 88
        box_w, box_h = 330, 590
        draw.rectangle((box_x, box_y, box_x + box_w, box_y + box_h),
                       outline=(63, 72, 86), width=1)
        xs, ys = [p[0] for p in projected], [p[1] for p in projected]
        scale = min((box_w - 44) / max(max(xs) - min(xs), 1),
                    (box_h - 44) / max(max(ys) - min(ys), 1))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        for x, y in projected:
            sx = box_x + box_w / 2 + (x - cx) * scale
            sy = box_y + box_h / 2 - (y - cy) * scale
            draw.ellipse((sx - 3, sy - 3, sx + 3, sy + 3), fill=(107, 212, 225))
        draw.text((box_x + 8, box_y + 8), label, fill=(230, 236, 241))
    draw.text((20, 20), f'3DMK ROW {mesh["row"]:02} | {len(verts)} raw coordinate samples',
              fill=(240, 240, 240))
    draw.text((20, height - 32), 'POINT CLOUD ONLY / no verified faces, bone placement, or identity',
              fill=(255, 160, 132))
    png = target / f'arcade-3dmk-row-{mesh["row"]:02}-pointcloud.png'
    image.save(png)
    return obj, png


def export_all(data, meshes, target):
    target.mkdir(parents=True, exist_ok=True)
    obj = target / 'arcade-3dmk-00-all-rows-unassembled-pointcloud.obj'
    lines = [
        '# All coordinate streams from the first 3DMK slice.',
        '# Rows are unassembled; no verified faces, bones, textures, or identity.',
    ]
    offset = 0
    populated = 0
    for mesh in meshes:
        verts = positions(data, mesh)
        if not verts:
            continue
        populated += 1
        lines.append(f'o row_{mesh["row"]:02}')
        lines.extend(f'v {x} {y} {z}' for x, y, z in verts)
        lines.extend(f'p {offset + i + 1}' for i in range(len(verts)))
        offset += len(verts)
    lines.append('')
    obj.write_text('\n'.join(lines), encoding='ascii')
    return obj, populated, offset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('slice', type=Path)
    parser.add_argument('--row', type=int, default=12)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('exports/arcade-3dmk'))
    args = parser.parse_args()
    data = args.slice.read_bytes()
    meshes = parse(data)
    if args.all:
        path, rows, points = export_all(data, meshes, args.output)
        print(path.resolve(), rows, 'nonempty rows', points, 'raw coordinate samples')
        return
    if args.row < 0 or args.row >= len(meshes):
        raise ValueError('row outside model table')
    for path in export(data, meshes[args.row], args.output):
        print(path.resolve())


if __name__ == '__main__':
    main()

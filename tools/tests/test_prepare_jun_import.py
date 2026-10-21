import struct
import unittest
import hashlib
import json
import tempfile
from pathlib import Path

from tools.prepare_jun_import import ROOT, check_textures, model_relocations, export_costumes


def tim(x=0, width=16, height=8):
    palette = struct.pack("<I4H", 44, 0, 1, 16, 1) + bytes(32)
    pixels = struct.pack("<I4H", 12 + width * height * 2, x, 0, width, height) + bytes(width * height * 2)
    return struct.pack("<II", 16, 8) + palette + pixels


class JunPreparationTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'workspace/jun-import/ttt1/bankedroms.bin').is_file(), 'private arcade bank required')
    def test_all_three_original_costumes(self):
        bank = (ROOT / 'workspace/jun-import/ttt1/bankedroms.bin').read_bytes()
        expected = json.loads((ROOT / 'tools/data/jun_runtime_hashes.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            report = export_costumes(bank, out)
            self.assertEqual([r['arcade_model'] for r in report], [46, 47, 118])
            self.assertEqual([r['texture_tiles'] for r in report], [26, 22, 28])
            self.assertEqual(len(list(out.iterdir())), 9)
            for path in out.iterdir():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected[path.name])
        with self.assertRaisesRegex(ValueError, 'source bank'):
            export_costumes(bank[:-1], Path('unused'))

    def test_relocations_require_full_live_match(self):
        raw = struct.pack("<4I", 12, 0, 7, 0)
        live = struct.pack("<4I", 0x8030000C, 0, 7, 0)
        self.assertEqual(model_relocations(raw, live, 0x80300000), [0])
        with self.assertRaisesRegex(ValueError, "Unexplained"):
            model_relocations(raw, live[:-4] + struct.pack("<I", 1), 0x80300000)

    def test_non_pointer_mutation_is_rejected(self):
        raw = struct.pack("<4I", 500, 0, 0, 0)
        live = struct.pack("<4I", 0x803001F4, 0, 0, 0)
        with self.assertRaises(ValueError):
            model_relocations(raw, live, 0x80300000)

    def test_all_tiles_and_arcade_terminator(self):
        tiles = check_textures(tim() + tim(64) + bytes(4))
        self.assertEqual([tile["x"] for tile in tiles], [0, 64])

    def test_rejects_tile_crossing_ps1_packing_boundary(self):
        with self.assertRaisesRegex(ValueError, "allocation"):
            check_textures(tim(60))

    def test_rejects_truncated_pixels(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            check_textures(tim()[:-2])

    def test_rejects_unrecognized_trailing_data(self):
        with self.assertRaises(ValueError):
            check_textures(tim() + b"\1\0\0\0")


if __name__ == "__main__":
    unittest.main()

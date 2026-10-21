"""Checks the optional Anna portrait conversion without launching the game."""
import struct
import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import tim_tool
from anna_portrait_pack import build


class AnnaPortraitTests(unittest.TestCase):
    def test_shipped_native_portrait(self):
        path = ROOT / 'mods/assets/anna-portrait/portrait.tim'
        data = path.read_bytes()
        tim = tim_tool.parse_tim(data)
        self.assertEqual((tim.pixel_width, tim.image.height), (126, 252))
        self.assertEqual(len(data), 544 + 126 * 252)
        self.assertEqual(struct.unpack_from('<HH', data, 540), (63, 252))
        rgba = tim_tool.decode_rgba(data, tim)
        self.assertEqual(rgba[3], 0)  # original black border is transparent
        self.assertTrue(any(rgba[i] == 255 for i in range(3, len(rgba), 4)))

    def test_source_and_preview_preserve_full_composition(self):
        folder = ROOT / 'mods/assets/anna-portrait'
        with Image.open(folder / 'portrait-source.png') as image:
            self.assertEqual(image.size, (887, 1774))
        with Image.open(folder / 'portrait-preview.png') as image:
            self.assertEqual(image.size, (126, 252))

    def test_non_portrait_input_rejected(self):
        with self.assertRaises(ValueError):
            with __import__('tempfile').TemporaryDirectory() as temp:
                folder = Path(temp)
                Image.new('RGB', (100, 100)).save(folder / 'square.png')
                build(folder / 'square.png', folder / 'out')


if __name__ == '__main__':
    unittest.main()

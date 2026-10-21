"""Synthetic UI conversion checks; no copyrighted fixtures required."""
import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
import prepare_jun_ui as ui

class JunUiTests(unittest.TestCase):
    def test_lz_roundtrip_and_rejected_truncation(self):
        data=bytes(range(256))*7
        packed=ui.literal_stream(data)
        self.assertEqual(ui.decompress(packed),(data,len(packed)))
        for bad in (b'',b'\x03',b'\x02\x00',b'\x02\x00\x01'):
            with self.assertRaises(ValueError):ui.decompress(bad)

    def test_portrait_palette_bands_and_transparency(self):
        im=Image.new('RGBA',(168,252),(0,0,0,0))
        for y,color in zip(range(0,252,64),('red','green','blue','white')):
            im.paste(color,(0,y,84,min(y+64,252)))
        tim=ui.ps1_tim(im,True)
        self.assertEqual(len(tim),544+126*252)
        self.assertEqual(struct.unpack_from('<HH',tim,540),(63,252))
        for y in range(252):
            pixels=tim[544+y*126:544+(y+1)*126]
            self.assertTrue(all(0<p<64 for p in pixels[:63]))
            self.assertEqual(pixels[63:],bytes(63))
        self.assertEqual([struct.unpack_from('<H',tim,20+i*128)[0] for i in range(4)],[0]*4)

    def test_name_preserves_source_nibbles(self):
        jin=Image.new('L',(20,16),3);julia=Image.new('L',(40,16),12)
        packed,im=ui.jun_name(jin,julia)
        self.assertEqual(len(packed),192)
        self.assertEqual(im.tobytes()[:24],bytes([3]*7+[12]*9+[3]*8))
        self.assertEqual(bytes(v for b in packed for v in (b&15,b>>4)),im.tobytes())

    def test_icons_keep_requested_height(self):
        for height in (29,34,58,68):
            tim=ui.ps1_tim(Image.new('RGBA',(44,height),'red'))
            self.assertEqual(struct.unpack_from('<HH',tim,540),(16,height))
            self.assertEqual(len(tim),544+32*height)

if __name__=='__main__':unittest.main()

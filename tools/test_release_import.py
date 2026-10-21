"""ROM-free checks for the public import verification boundary."""
from pathlib import Path
import hashlib, json, tempfile, unittest, zipfile, zlib
from unittest.mock import patch
import arcade_model_probe as probe
import prepare_jun_import as prepare

class ImportVerification(unittest.TestCase):
    def test_renamed_chip_requires_matching_content(self):
        data=b'handwritten synthetic ROM fixture'
        spec={'name':'new-name','operation':'ROM_LOAD','offset':0,'size':len(data),
              'crc32':f'{zlib.crc32(data):08x}','sha1':hashlib.sha1(data).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'set.zip'
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('old-name',data)
            definition={'regions':[{'name':'test','size':len(data),'loads':[spec]}]}
            self.assertEqual(probe.reconstruct(path,definition)[0]['test'],data)
            spec['sha1']='0'*40
            with self.assertRaises(probe.ProbeError):probe.reconstruct(path,definition)

    def test_capture_ignores_scratch_but_rejects_consumed_byte_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'tools/data').mkdir(parents=True)
            ram=bytearray(0x400000);ram[100:104]=b'TEST'
            data={'jun-select-ram.bin':[{'offset':100,'size':4,'sha256':hashlib.sha256(b'TEST').hexdigest()}]}
            (root/'tools/data/jun_capture_ranges.json').write_text(json.dumps(data))
            path=root/'jun-select-ram.bin';path.write_bytes(ram)
            with patch.object(prepare,'ROOT',root):
                self.assertEqual(prepare.verified(path,'old-snapshot'),ram)
                ram[0]=1;path.write_bytes(ram)
                self.assertEqual(prepare.verified(path,'old-snapshot'),ram)
                ram[101]=0;path.write_bytes(ram)
                with self.assertRaises(ValueError):prepare.verified(path,'old-snapshot')

if __name__=='__main__':unittest.main()

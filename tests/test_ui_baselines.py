import copy,hashlib,io,json,tarfile,tempfile,unittest
from pathlib import Path
from profile_ui import historical_baseline

class HistoricalBaselines(unittest.TestCase):
    def prepare(self,folder):
        root=Path(folder);manifest={'schema':1,'baselines':{}}
        for name,path in [('source','src/home.c'),('deployment','deploy/app/font.ttf')]:
            archive=root/(name+'.tar.gz');data=b'exact historic input'
            with tarfile.open(archive,'w:gz') as packed:
                member=tarfile.TarInfo(path);member.size=len(data);member.mode=0o644
                packed.addfile(member,io.BytesIO(data))
            spec={'file':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'input_files':{path:hashlib.sha256(data).hexdigest()}}
            if name=='source':
                spec.update(original_archive_sha256='original',original_release='original-release')
                manifest['baselines']['v2.0.2.3']=spec
            else:manifest['deployment']=spec
        (root/'manifest.json').write_text(json.dumps(manifest));return root,manifest

    def test_exact_inputs_and_original_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root,manifest=self.prepare(folder)
            evidence=historical_baseline('v2.0.2.3',root/'checkout',root)
            self.assertEqual(evidence['source_sha256'],'original')
            self.assertEqual((root/'checkout/src/home.c').read_bytes(),b'exact historic input')
            self.assertTrue((root/'checkout/deploy/app/font.ttf').is_file())

    def test_corrupt_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root,manifest=self.prepare(folder);(root/'source.tar.gz').write_bytes(b'corrupt')
            with self.assertRaisesRegex(RuntimeError,'digest mismatch'):
                historical_baseline('v2.0.2.3',root/'checkout',root)

    def test_missing_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root,manifest=self.prepare(folder)
            manifest['deployment']['input_files']['deploy/missing']='missing'
            (root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(RuntimeError,'inventory mismatch'):
                historical_baseline('v2.0.2.3',root/'checkout',root)

    def test_unsafe_paths_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root,manifest=self.prepare(folder);archive=root/'source.tar.gz';data=b'unsafe'
            with tarfile.open(archive,'w:gz') as packed:
                m=tarfile.TarInfo('../escape');m.size=len(data);packed.addfile(m,io.BytesIO(data))
            spec=manifest['baselines']['v2.0.2.3']
            spec.update(sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),input_files={'../escape':hashlib.sha256(data).hexdigest()})
            (root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(tarfile.FilterError):
                historical_baseline('v2.0.2.3',root/'checkout',root)
            self.assertFalse((root/'escape').exists())

if __name__=='__main__':unittest.main()

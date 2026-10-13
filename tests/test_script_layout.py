"""Catch broken relocation references before cloud builds start."""
from pathlib import Path
import re,shutil,tempfile,unittest
from unittest.mock import patch
import integration
from ci_impact import classify

ROOT=Path(__file__).resolve().parents[1]

class ScriptLayout(unittest.TestCase):
    def test_workflow_entry_points_exist_and_inline_imports_have_scripts_path(self):
        names={p.name for p in (ROOT/'scripts').iterdir() if p.suffix in ('.py','.sh')}
        for workflow in (ROOT/'.github/workflows').glob('*.yml'):
            text=workflow.read_text()
            imports='|'.join(re.escape(Path(name).stem) for name in names)
            if re.search(r'(?<![/\w.-])scripts/',text) or re.search(r'\b(?:from|import) (?:'+imports+r')\b',text):
                self.assertIn('PYTHONPATH: ${{ github.workspace }}/scripts',text)
            for name in names:
                self.assertIsNone(re.search(r'(?<![\w/.-])'+re.escape(name)+r'(?![\w.-])',text),(workflow,name))
            for name in re.findall(r'(?<![/\w.-])scripts/([\w-]+\.(?:py|sh))',text):
                self.assertTrue((ROOT/'scripts'/name).is_file(),(workflow,name))

    def test_relocated_scripts_remain_in_source_fingerprint(self):
        integration.unpack()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'integration').mkdir()
            registry=root/'integration/manifest.json';registry.write_bytes(integration.REGISTRY.read_bytes())
            shutil.copytree(ROOT/'scripts',root/'scripts')
            with patch.object(integration,'ROOT',root),patch.object(integration,'REGISTRY',registry):
                before=integration.fingerprint()
                file=root/'scripts/update_guard.py'
                file.write_bytes(file.read_bytes()+b'\n# fixture change\n')
                self.assertNotEqual(before,integration.fingerprint())

    def test_new_paths_preserve_conservative_native_and_compiler_gates(self):
        for path in ('scripts/integration.py','scripts/tizen-build.sh','build-inputs/integration-bundle.zip'):
            self.assertEqual(classify([path])['native_platforms'],['tizen','webos'])
        self.assertTrue(classify(['scripts/ci_compile.py'])['compiler_equivalence_required'])
        with self.assertRaisesRegex(ValueError,'Unclassified'):classify(['build-inputs/unknown.bin'])

if __name__=='__main__':unittest.main()

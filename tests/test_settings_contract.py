import tempfile,unittest
from pathlib import Path
from integration import settings_scene_contract,Incompatible

class SettingsSceneContract(unittest.TestCase):
    def fixture(self,folder,table):
        src=Path(folder)/'src';src.mkdir()
        (src/'mdbsettings_scene_cases.inc').write_text('case AJ_CUSTOM: return AJC_CUSTOM;')
        (src/'mdbsettings_tracking.inc').write_text('SEC("Tracking"), OPC(AJ_CUSTOM),')
        (src/'ajustes_ux_secoes.inc').write_text('static int ajCenaSecao(int op) { switch (op) {\n'
            '#include "mdbsettings_scene_cases.inc"\ncase AJ_FIRST: case AJ_SECOND: return AJC_SHARED;\n'
            'case AJ_OTHER: return AJC_OTHER;\ndefault: return -1; }}')
        (src/'ajustes_ux_tela.inc').write_text(table+'\n#include "mdbsettings_tracking.inc"')
        return Path(folder)
    def test_contiguous_scene_and_advanced_references_are_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            root=self.fixture(folder,'SEC("First"),OPC(AJ_FIRST),OPC(AJ_SECOND),'
                'SEC("Second"),OPC(AJ_OTHER),MAIS(),OPC(AJ_FIRST),')
            self.assertEqual(settings_scene_contract(root)['AJ_CUSTOM'],'AJC_CUSTOM')
    def test_noncontiguous_basic_scene_reuse_blocks_compatibility(self):
        with tempfile.TemporaryDirectory() as folder:
            root=self.fixture(folder,'SEC("First"),OPC(AJ_FIRST),OPC(AJ_OTHER),OPC(AJ_SECOND),')
            with self.assertRaisesRegex(Incompatible,'AJ_SECOND / AJC_SHARED'):settings_scene_contract(root)
    def test_changed_upstream_switch_does_not_silently_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root=self.fixture(folder,'SEC("First"),OPC(AJ_FIRST),')
            p=root/'src/ajustes_ux_secoes.inc';p.write_text(p.read_text().replace('int op','unsigned op'))
            with self.assertRaisesRegex(Incompatible,'format changed'):settings_scene_contract(root)

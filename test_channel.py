from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from channel import needed, version
from shell_id import shell_id

class Releases(unittest.TestCase):
    def test_first_release(self):
        self.assertTrue(needed({'id': 10}, None))

    def test_published_release_not_rebuilt(self):
        self.assertFalse(needed({'id': 10}, {'body': '<!-- upstream-release: 10 -->'}))

    def test_new_release_rebuilt(self):
        self.assertTrue(needed({'id': 11}, {'body': '<!-- upstream-release: 10 -->'}))

    def test_forced_patch_refresh(self):
        self.assertTrue(needed({'id': 10}, {'body': '<!-- upstream-release: 10 -->'}, True))

    def test_unpublished_and_prerelease_skipped(self):
        self.assertFalse(needed({'id': 10, 'draft': True}, None, True))
        self.assertFalse(needed({'id': 10, 'prerelease': True}, None, True))

    def test_version_input(self):
        self.assertEqual(version('v2.0.2'), '2.0.2')
        for bad in ['v2.0.2-beta', 'v2.0.2;echo unsafe', '../main', 'v2.0']:
            with self.assertRaises(ValueError): version(bad)

class ShellIdentity(unittest.TestCase):
    def test_changes_and_windows_line_endings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cs = root / 'tizen-tpk/Program.cs'; cs.parent.mkdir(parents=True)
            cs.write_bytes(b'host-v1\nline2\n')
            manifest = root / 'tizen-tpk/NuvioTpk/tizen-manifest.xml'
            manifest.parent.mkdir(); manifest.write_text('<manifest api-version="8" version="2.0.2"/>')
            engine = root / 'engine.so'; engine.write_bytes(b'engine-v1')
            initial = shell_id(root, engine)
            cs.write_bytes(b'host-v1\r\nline2\r\n')
            self.assertEqual(shell_id(root, engine), initial)
            manifest.write_text('<manifest api-version="8" version="2.0.3"/>')
            self.assertEqual(shell_id(root, engine), initial)
            manifest.write_text('<manifest api-version="9" version="2.0.3"/>')
            self.assertNotEqual(shell_id(root, engine), initial)
            manifest.write_text('<manifest api-version="8" version="2.0.3"/>')
            engine.write_bytes(b'engine-v2')
            self.assertNotEqual(shell_id(root, engine), initial)
            engine.write_bytes(b'engine-v1')
            art = root / 'deploy/app/art/marcas/logo.png'; art.parent.mkdir(parents=True); art.write_bytes(b'new-art')
            self.assertNotEqual(shell_id(root, engine), initial)

if __name__ == '__main__': unittest.main()

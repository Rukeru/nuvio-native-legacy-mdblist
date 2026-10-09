import hashlib
from pathlib import Path
import tempfile
import unittest
from tizen_improvements import changelog

class ChangelogTests(unittest.TestCase):
    def test_future_public_release_and_bounded_plain_notes(self):
        state={'upstream':{'tag_name':'v2.0.3','body':'<!-- hidden -->\n- Faster Home\n- Fixed [episode titles](https://example.test)\n- Quote " and slash \\ and café\n```\n- hidden command\n```\n- Download the package\n- '+('very long ' * 100)}}
        with tempfile.TemporaryDirectory() as folder:
            notes=changelog(folder,state)
            header=(Path(folder)/'src/mdbchangelog_notes.h').read_text(encoding='utf8')
            self.assertEqual(len(notes),7)
            self.assertIn('Nuvio 2.0.3',header)
            self.assertIn('Fixed episode titles',header)
            self.assertNotIn('https://',header)
            self.assertNotIn('hidden command',header)
            self.assertNotIn('Download the package',header)
            self.assertIn('\\"',header)
            self.assertIn('café',header)
            self.assertEqual(state['installed_changelog']['sha256'],hashlib.sha256((Path(folder)/'src/mdbchangelog_notes.h').read_bytes()).hexdigest())
    def test_no_release_notes_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(len(changelog(folder,{'upstream':{'tag_name':'v2.0.4','body':None}})),4)

if __name__=='__main__':unittest.main()

import hashlib,json
from pathlib import Path
import tempfile,os,unittest
from unittest.mock import patch
from profile_ui import changelog_only

class ProfileRules(unittest.TestCase):
    def test_reuse_only_identical_history_and_upstream_with_additive_changelog(self):
        before=[{'patch':'shared-08-watched-history-sync.patch','sha256':'fixture'}]
        after=before+[{'patch':'shared-09-installed-changelog.patch','sha256':'new'},
                      {'patch':'shared-10-changelog-modal-guards.patch','sha256':'guards'},
                      {'patch':'shared-11-changelog-readability.patch','sha256':'readability'}]
        old={'upstream_commit':'base','tizen_improvements':before}
        new={'upstream_commit':'base','tizen_improvements':after}
        with tempfile.TemporaryDirectory() as folder:
            saved=os.getcwd()
            try:
                os.chdir(folder)
                def check(previous,current):
                    Path('state.json').write_text(json.dumps(current))
                    data=json.dumps(previous).encode()
                    release=json.dumps({'html_url':'https://github.com/fixture/release','assets':[{'name':'SOURCE.json','browser_download_url':'https://example.test/source','digest':'sha256:'+hashlib.sha256(data).hexdigest()}]}).encode()
                    with patch('profile_ui.fetch',side_effect=[release,data]):return changelog_only(Path(folder))
                self.assertIsNotNone(check(old,new))
                self.assertIsNone(check(old,{**new,'upstream_commit':'changed'}))
                self.assertIsNone(check({**old,'tizen_improvements':[]},new))
                with patch('profile_ui.fetch') as fetch:
                    Path('state.json').write_text(json.dumps({**new,'tizen_improvements':after+[{'patch':'next-performance.patch'}]}))
                    self.assertIsNone(changelog_only(Path(folder)));fetch.assert_not_called()
            finally:os.chdir(saved)

if __name__=='__main__':unittest.main()

import hashlib, io, json, subprocess, tempfile, unittest, urllib.error
from pathlib import Path
from unittest.mock import patch
import integration, update_guard
from resilience import retry

# Simulated conflicts must exercise real diagnostics without contaminating the
# actual Actions summary. Restore the runner environment before real preflight.
_summary_environment = patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': ''})
def setUpModule(): _summary_environment.start()
def tearDownModule(): _summary_environment.stop()

class ReleaseMonitor(unittest.TestCase):
    def test_workflow_command_line_flags(self):
        a=update_guard.arguments(['run','--platform','tizen','--state','state.json','--stage','preflight','--','bash','preflight.sh','tizen'])
        self.assertEqual(a.platform,'tizen');self.assertEqual(a.command,['bash','preflight.sh','tizen'])
        a=update_guard.arguments(['failure','--platform','webos','--state','webos-state.json'])
        self.assertEqual(a.command,[])
    def test_unsorted_platform_releases_and_prerelease(self):
        rows=[{'tag_name':tag,'id':i,'prerelease':pre} for tag,i,pre in [
            ('v2.0.2.19',9,False),('webos-v2.0.300015',8,False),('v2.0.3.21',7,False),
            ('v9.0.0',10,True),('webos-v2.0.200012',11,False)]]
        self.assertEqual(update_guard.stable(rows)['tag_name'],'v2.0.3.21')
        self.assertEqual(update_guard.stable(rows,'webos-v')['tag_name'],'webos-v2.0.300015')
    def test_pagination_is_not_first_page_only(self):
        with patch('update_guard.api',side_effect=[[{'id':i} for i in range(100)],[{'id':101}]]):
            self.assertEqual(len(update_guard.pages('repos/example/releases')),101)
    def test_conflict_quarantine_and_force(self):
        state={'upstream':{'id':5}}
        with patch('integration.fingerprint',return_value='aaa'),patch('update_guard.issues',return_value=[{'body':'<!-- update-block: tizen:5:aaa -->','html_url':'fixture'}]):
            self.assertTrue(update_guard.blocked('tizen',state))
            self.assertFalse(update_guard.blocked('webos',state))
            self.assertFalse(update_guard.blocked('tizen',state,True))
        with patch('integration.fingerprint',return_value='repair'),patch('update_guard.issues',return_value=[{'body':'<!-- update-block: tizen:5:aaa -->','html_url':'fixture'}]):
            self.assertFalse(update_guard.blocked('tizen',state))

class Retries(unittest.TestCase):
    def test_transient_get_retries_but_auth_and_conflicts_do_not(self):
        for code,expected in [(503,3),(429,3),(401,1),(403,1),(404,1)]:
            with patch('time.sleep') as sleep:
                operation=__import__('unittest.mock',fromlist=['Mock']).Mock(side_effect=urllib.error.HTTPError('fixture',code,'fixture',{},None))
                with self.assertRaises(urllib.error.HTTPError):retry(operation,sleep=sleep)
                self.assertEqual(operation.call_count,expected)
        operation=__import__('unittest.mock',fromlist=['Mock']).Mock(side_effect=integration.Incompatible('Settings conflict'))
        with self.assertRaises(integration.Incompatible):retry(operation,sleep=lambda _:None)
        self.assertEqual(operation.call_count,1)
    def test_command_classifier(self):
        for text in ['CONFLICT Settings','file.c:22:3: error: incompatible interface\nConnection timed out','Assertion failed','checksum mismatch']:
            self.assertFalse(update_guard.network_log(text))
        for text in ['fatal: unable to access URL: The requested URL returned error: 503','Could not resolve host: github.com','net/http: TLS handshake timeout']:
            self.assertTrue(update_guard.network_log(text))
    def test_source_failure_is_run_once(self):
        with patch('update_guard.subprocess.Popen') as run:
            process=run.return_value.__enter__.return_value
            process.stdout=io.StringIO('CONFLICT Settings\n');process.wait.return_value=1
            with self.assertRaises(subprocess.CalledProcessError):update_guard.network_command(['git'],sleep=lambda _:None)
            self.assertEqual(run.call_count,1)
    def test_transient_command_can_recover_and_keeps_complete_output(self):
        from unittest.mock import MagicMock
        first=MagicMock();first.__enter__.return_value.stdout=io.StringIO('Could not resolve host: github.com\n');first.__enter__.return_value.wait.return_value=1
        second=MagicMock();second.__enter__.return_value.stdout=io.StringIO('download completed\n');second.__enter__.return_value.wait.return_value=0
        with patch('update_guard.subprocess.Popen',side_effect=[first,second]) as run:
            update_guard.network_command(['download'],sleep=lambda _:None)
            self.assertEqual(run.call_count,2)

class ComponentMerge(unittest.TestCase):
    def fixture(self,root):
        subprocess.run(['git','init',str(root)],check=True,stdout=subprocess.DEVNULL)
        self.git(root,'config','user.name','Fixture');self.git(root,'config','user.email','fixture@example.test')
        self.git(root,'config','core.autocrlf','false')
        (root/'settings.c').write_bytes(b'before\nsetting\nafter\n')
        self.git(root,'add','.');self.git(root,'commit','-m','base')
        (root/'settings.c').write_bytes(b'before\nMDBList\nafter\n')
        data=self.git(root,'diff','--full-index').encode()
        self.git(root,'checkout','--','settings.c')
        return data
    def git(self,root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True)
    def test_compatible_upstream_edit_merges_and_conflict_names_component(self):
        for conflict in [False,True]:
            with tempfile.TemporaryDirectory() as temp:
                temp=Path(temp);root=temp/'upstream';bundle=temp/'integration';bundle.mkdir()
                data=self.fixture(root);(bundle/'settings.patch').write_bytes(data)
                m={'base_commit':'fixture','overlay':[],'components':[{'name':'settings','platforms':['tizen'],'patch':'settings.patch','sha256':hashlib.sha256(data).hexdigest(),'files':['settings.c']}]}
                if conflict:(root/'settings.c').write_bytes(b'before\nnew upstream setting\nafter\n')
                else:(root/'new-upstream.c').write_bytes(b'independent upstream feature\n')
                self.git(root,'add','.');self.git(root,'commit','-m','upstream')
                state={'upstream':{'tag_name':'v2.0.4'}}
                with patch.object(integration,'ROOT',temp),patch.object(integration,'manifest',return_value=m),patch.object(integration,'fingerprint',return_value='fixture'),patch.object(integration,'contracts'),patch('tizen_improvements.changelog'):
                    if conflict:
                        with self.assertRaises(integration.Incompatible):integration.apply(root,'tizen',state)
                        report=json.loads((temp/'diagnostics/tizen-compatibility.json').read_text())
                        self.assertEqual(report['component'],'settings');self.assertEqual(report['files'],['settings.c'])
                    else:
                        integration.apply(root,'tizen',state)
                        self.assertIn('MDBList',(root/'settings.c').read_text())
                        self.assertTrue((root/'new-upstream.c').exists())
    def test_registry_inputs_are_checked(self):
        m=integration.manifest()
        for e in m['overlay']:integration.verified(integration.ROOT/'integration/overlay'/e['path'],e['sha256'])
        for c in m['components']:integration.verified(integration.ROOT/'integration'/c['patch'],c['sha256'])
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'corrupt.patch';p.write_text('changed')
            with self.assertRaises(integration.Incompatible):integration.verified(p,'0'*64)

if __name__=='__main__':unittest.main()

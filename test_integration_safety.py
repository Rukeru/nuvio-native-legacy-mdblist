import hashlib, http.client, json, socket, ssl, subprocess, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch, Mock
from urllib.error import HTTPError

import integration, release_http, update_guard
from resilience import transient


class BundleSafety(unittest.TestCase):
    def test_unpack_verifies_digest_and_paths_before_writing(self):
        for name, corrupt, success in [('manifest.json', False, True), ('../escape', False, False),
                                       ('folder\\escape', False, False), ('manifest.json', True, False)]:
            with self.subTest(name=name, corrupt=corrupt), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); archive=root/'integration-bundle.zip'
                info=zipfile.ZipInfo('fixture');info.filename=name
                with zipfile.ZipFile(archive,'w') as z:z.writestr(info,'{}')
                digest='0'*64 if corrupt else hashlib.sha256(archive.read_bytes()).hexdigest()
                (root/'integration-bundle.sha256').write_text(digest)
                with patch.object(integration,'ROOT',root), patch.object(integration,'REGISTRY',root/'integration/manifest.json'):
                    if success:
                        integration.unpack();self.assertEqual(json.loads((root/'integration/manifest.json').read_text()),{})
                    else:
                        with self.assertRaises(integration.Incompatible):integration.unpack()
                        self.assertFalse((root/'integration').exists())

    def test_keyed_translations_preserve_upstream_additions_and_reject_conflicts(self):
        for conflict in (False, True):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); source=root/'upstream'; (source/'src').mkdir(parents=True); (root/'integration').mkdir()
                value='Changed upstream' if conflict else 'Old'
                table=source/'src/idioma_tab.h'
                table.write_text('static const char *rows[][2] = {\n  { "Owned", "'+value+'" },\n  { "Upstream", "New native label" },\n};\n')
                spec=root/'integration/translations.json'
                spec.write_text(json.dumps({'entries':[{'key':'"Owned"','english':'"MDBList"','previous':'"Old"'}]}))
                manifest={'translations':{'file':'translations.json','sha256':hashlib.sha256(spec.read_bytes()).hexdigest()}}
                with patch.object(integration,'ROOT',root), patch.object(integration,'git'), patch.object(integration,'report') as report:
                    if conflict:
                        with self.assertRaises(integration.Incompatible):integration.translations(source,'tizen',{},manifest)
                        self.assertEqual(report.call_args.args[2:4],('translations','source-conflict'))
                    else:
                        integration.translations(source,'tizen',{},manifest)
                        self.assertIn('"New native label"',table.read_text()); self.assertIn('"MDBList"',table.read_text())


class PublicationRecovery(unittest.TestCase):
    def test_connection_loss_is_retryable_but_certificate_and_source_errors_are_not(self):
        for error in (http.client.IncompleteRead(b'partial'),ssl.SSLEOFError('connection lost'),socket.gaierror(socket.EAI_AGAIN,'temporary DNS')):
            self.assertTrue(transient(error))
        for error in (ssl.SSLCertVerificationError('certificate invalid'),socket.gaierror(socket.EAI_NONAME,'invalid host'),ValueError('checksum mismatch')):
            self.assertFalse(transient(error))
    def response_loss(self):return HTTPError('fixture',503,'response lost',{},None)
    def test_completed_upload_is_recovered_without_reposting(self):
        data=b'checked package';asset={'id':7,'name':'app.ipk','digest':'sha256:'+hashlib.sha256(data).hexdigest()}
        with patch.dict('os.environ',{'GH_TOKEN':'fixture'}), patch('release_http.urllib.request.urlopen',side_effect=self.response_loss()) as post, patch('release_http.api',return_value={'draft':True,'assets':[asset]}), patch('release_http.time.sleep'):
            result=release_http.request('https://uploads.github.com/repos/fixture/releases/12/assets?name=app.ipk',data,binary=True)
            self.assertEqual(result,asset);self.assertEqual(post.call_count,1)
    def test_ambiguous_upload_never_modifies_live_release(self):
        with patch.dict('os.environ',{'GH_TOKEN':'fixture'}), patch('release_http.urllib.request.urlopen',side_effect=self.response_loss()) as post, patch('release_http.api',return_value={'draft':False,'assets':[]}), patch('release_http.delete_asset') as delete:
            with self.assertRaisesRegex(RuntimeError,'live release'):release_http.request('https://uploads.github.com/repos/fixture/releases/12/assets?name=app.ipk',b'package',binary=True)
            delete.assert_not_called();self.assertEqual(post.call_count,1)
    def test_ambiguous_draft_creation_recovers_exact_tag(self):
        draft={'id':7,'tag_name':'v2.0.3.21','draft':True}
        with patch.dict('os.environ',{'GH_TOKEN':'fixture'}), patch('release_http.urllib.request.urlopen',side_effect=self.response_loss()) as post, patch('update_guard.pages',return_value=[draft]):
            self.assertEqual(release_http.request('https://api.github.com/repos/fixture/releases',{'tag_name':draft['tag_name']}),draft)
            self.assertEqual(post.call_count,1)


class IssueRecovery(unittest.TestCase):
    def test_component_and_affected_files_survive_a_failed_check(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/'state.json';state.write_text('{}')
            output='src/contalib.c:44: error: changed interface\n::integration-component::account-history-tests\n'
            error=subprocess.CalledProcessError(1,['check'],output=output)
            with patch('update_guard.network_command',side_effect=error),patch('integration.report') as report:
                with self.assertRaises(subprocess.CalledProcessError):update_guard.run('webos',state,'preflight',['check'])
                self.assertEqual(report.call_args.args[2:4],('account-history-tests','check-failure'))
                self.assertEqual(report.call_args.args[-1],['src/contalib.c'])
    def test_known_failure_is_not_reported_twice_and_recovery_closes_it(self):
        state={'upstream':{'id':5,'tag_name':'v2.0.3'}}
        issue={'number':7,'html_url':'fixture','body':'<!-- update-block: tizen:5:aaa -->'}
        diagnostic={'status':'source-conflict','component':'settings','files':['settings.c'],'run_url':'fixture','details':'CONFLICT'}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'diagnostics').mkdir();(root/'state.json').write_text(json.dumps(state))
            (root/'diagnostics/tizen-compatibility.json').write_text(json.dumps(diagnostic))
            with patch.object(integration,'ROOT',root), patch('integration.fingerprint',return_value='aaa'), patch('update_guard.issues',return_value=[issue]), patch('update_guard.api') as api:
                update_guard.failure('tizen',root/'state.json');api.assert_not_called()
                update_guard.recovered('tizen',state)
                self.assertEqual(api.call_args.args[1],{'state':'closed','state_reason':'completed'})


if __name__=='__main__':unittest.main()

"""Cross-language protocol and maintained integration checks (not native runtime proof)."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile,unittest,zipfile
import integration
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]

class PrivateClient(unittest.TestCase):
    def test_activation_fails_closed_if_verified_inputs_change(self):
        integration.unpack()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'src').mkdir()
            state={'builder_commit':'0123456789abcdef0123456789abcdef01234567'}
            integration.diagnostic_build(root,state)
            # Explicit user policy overrides completed historical security proof.
            self.assertFalse(state['private_diagnostics']['production_enabled'])
            self.assertIn('#define NV_DIAG_VERIFIED 0',(root/'src/nvdiag_build.h').read_text())
            original=integration.verified
            def changed(path,digest):
                if path.name=='nvdiag.c':raise integration.Incompatible('Changed client needs reverification')
                return original(path,digest)
            with patch.object(integration,'verified',side_effect=changed):
                with self.assertRaises(integration.Incompatible):integration.diagnostic_build(root,state)
            integration.diagnostic_build(root,{})
            self.assertIn('#define NV_DIAG_VERIFIED 0',(root/'src/nvdiag_build.h').read_text())

    def test_generated_provenance_is_exact_and_rejects_injection(self):
        integration.unpack()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'src').mkdir()
            state={'builder_commit':'0123456789abcdef0123456789abcdef01234567'}
            integration.diagnostic_build(root,state)
            header=(root/'src/nvdiag_build.h').read_text()
            self.assertIn('#define NV_DIAG_BUILD "'+state['builder_commit']+'"',header)
            self.assertEqual(state['private_diagnostics']['header_sha256'],hashlib.sha256((root/'src/nvdiag_build.h').read_bytes()).hexdigest())
            with self.assertRaises(integration.Incompatible):
                integration.diagnostic_build(root,{'builder_commit':'"; private_token'})

    def test_numeric_client_events_match_independent_worker_schema(self):
        with zipfile.ZipFile(ROOT/'build-inputs/integration-bundle.zip') as bundle:
            source=bundle.read('overlay/src/nvdiag_format.c').decode()
        rows=re.findall(r'\{"([a-z_]+)","([a-z_]+)",(NULL|"[a-z_]+"),(\d+),(\d+),(\d+)\}',source)
        self.assertEqual(len(rows),18)
        reports=[]
        for code,a,b,minimum,maximum,max_b in rows:
            context={a:int(maximum)}
            if b!='NULL':context[json.loads(b)]=int(max_b)
            reports.append(dict(version=1,report_id='12345678-1234-4123-8123-123456789abc',
                platform='tizen',app_version='2.0.4.64',build_id='0123456789abcdef0123456789abcdef01234567',
                events=[dict(code=code,context=context)]))
        program="""
        import {validateReport,EVENTS} from './private-diagnostics/ingestion.mjs';
        let input='';for await(const chunk of process.stdin)input+=chunk;
        const reports=JSON.parse(input);
        if(reports.length!==Object.keys(EVENTS).length)throw new Error('event inventory drift');
        for(const r of reports){validateReport(r);r.events[0].context.private_url='secret';
          let rejected=false;try{validateReport(r);}catch{rejected=true;}
          if(!rejected)throw new Error('privacy regression');}
        """
        subprocess.run(['node','--input-type=module','-e',program],cwd=ROOT,input=json.dumps(reports),text=True,check=True)

    def test_owned_transport_and_adapter_are_in_verified_bundle(self):
        archive=ROOT/'build-inputs/integration-bundle.zip'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),(ROOT/'build-inputs/integration-bundle.sha256').read_text().strip())
        with zipfile.ZipFile(archive) as bundle:
            manifest=json.loads(bundle.read('manifest.json'))
            component=next(c for c in manifest['components'] if c['name']=='private-diagnostics')
            self.assertEqual(set(component['platforms']),{'tizen','webos'})
            self.assertEqual(hashlib.sha256(bundle.read(component['patch'])).hexdigest(),component['sha256'])
            client=bundle.read('overlay/src/nvdiag.c').decode()
            self.assertNotIn('NV_REC_URL',client)
            self.assertNotIn('sessao_token',client)
            self.assertNotIn('trakt_cabecalhos',client)
            for protection in ('request.max_bytes=4096','request.seguir=0','request.tls_pessoal=0',
                               'dados_gravar_privado','/dev/urandom','queue[index].attempts=8'):
                self.assertIn(protection,client)
            fixture=bundle.read('overlay/tests/tizen_improvements.sh').decode()
            self.assertIn('tests/nvdiag.c src/nvdiag_format.c src/js.c',fixture)
            self.assertIn('"$out/private-diagnostics"',fixture)

if __name__=='__main__':unittest.main()

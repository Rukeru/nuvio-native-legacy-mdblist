import json,tempfile,unittest
from pathlib import Path
from regression_gate import attest,validate

class RegressionGate(unittest.TestCase):
    def test_deployed_bash_scripts_do_not_contain_windows_line_endings(self):
        scripts=list(Path(__file__).parent.glob('*.sh'))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):self.assertNotIn(b'\r',script.read_bytes())
    def test_complete_execution_requires_zero_unverified_skips(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.json';summary=Path(d)/'summary.txt'
            state.write_text(json.dumps({'upstream_commit':'source','builder_commit':'builder','integration':{'fingerprint':'reviewed'}}))
            summary.write_text('shard 0: testes: 20 passaram, 0 falharam, 0 SKIP sem prova, 0 fora da suite\nok    mdblist_settings_defaults.sh\ntestes: 500 passaram, 0 falharam, 2 SKIP sem prova, 75 fora da suite; logs: fixture\n')
            with self.assertRaisesRegex(ValueError,'completely'):attest(state,summary)
            summary.write_text(summary.read_text().replace('2 SKIP sem prova','0 SKIP sem prova'))
            attest(state,summary)
            data=json.loads(state.read_text());result=validate(data,state)
            self.assertEqual(result['passed'],500);self.assertEqual(result['unavailable'],0)
    def test_missing_failed_or_skipped_execution_cannot_authorize_release(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.json';summary=Path(d)/'summary.txt';state.write_text('{}')
            for text in ('Skipped workflow','testes: 0 passaram, 0 falharam, 1 SKIP sem prova, 75 fora da suite',
                         'testes: 500 passaram, 1 falharam, 0 SKIP sem prova, 75 fora da suite',
                         'testes: 500 passaram, 0 falharam, 0 SKIP sem prova, 75 fora da suite'):
                summary.write_text(text)
                with self.subTest(text=text),self.assertRaises(ValueError):attest(state,summary)
    def test_different_source_builder_or_integration_cannot_reuse_evidence(self):
        base={'upstream_commit':'source','builder_commit':'builder','integration':{'fingerprint':'reviewed'},
              'full_regression':{'outcome':'passed','passed':500,'failed':0}}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';p.write_text(json.dumps(base))
            for changed in ({**base,'upstream_commit':'different'}, {**base,'builder_commit':'different'},
                            {**base,'integration':{'fingerprint':'different'}}):
                with self.subTest(changed=changed),self.assertRaises(ValueError):validate(changed,p)

    def test_diagnostic_results_never_authorize_publication(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';p.write_text('{"diagnostic_only":true}')
            with self.assertRaisesRegex(ValueError,'Diagnostic'):validate({},p)

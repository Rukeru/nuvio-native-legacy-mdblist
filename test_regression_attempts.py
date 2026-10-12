import hashlib,json,tempfile,unittest
from pathlib import Path
from regression_attempts import select


class RetryEvidence(unittest.TestCase):
    def fixture(self,root,index,artifact_attempt,code=0,**changes):
        artifact=root/f'tizen-regression-shard-{index}-attempt-{artifact_attempt}'
        folder=artifact/'regression-logs'/f'shard-{index}';folder.mkdir(parents=True)
        summary=b'original assertion evidence\n';(folder/'SUMMARY.txt').write_bytes(summary)
        meta={'index':index,'count':2,'attempt':artifact_attempt,'run_id':'123','exit_code':code,
              'state':{'upstream_commit':'u','builder_commit':'b','integration':{'fingerprint':'f'}},
              'gatekeeper_sha256':'g','files':['a','b'],'environment':{'os':'Darwin','image':'same'},
              'summary_sha256':hashlib.sha256(summary).hexdigest(),**changes}
        (folder/'execution.json').write_text(json.dumps(meta))
        return artifact

    def test_failed_attempt_retained_successful_shard_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'input';output=Path(d)/'output'
            failed=self.fixture(root,0,1,1);self.fixture(root,0,2);self.fixture(root,1,1)
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            select(root,output,'tizen',2,'123')
            self.assertEqual(json.loads((output/'ATTEMPTS.json').read_text())['selected'],{'0':2,'1':1})
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
            self.assertTrue(failed.exists())

    def test_no_fallback_to_earlier_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'input';self.fixture(root,0,1);self.fixture(root,0,2,1);self.fixture(root,1,1)
            with self.assertRaisesRegex(ValueError,'Latest'):select(root,Path(d)/'out','tizen',2,'123')

    def test_rejects_mismatched_source_run_environment_missing_or_corrupt(self):
        for changed in ({'run_id':'other'},{'attempt':9},{'environment':{}},
                        {'state':{'upstream_commit':'different'}},{'summary_sha256':'corrupt'},
                        {'environment':{'os':'changed'}}):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as d:
                root=Path(d)/'input';self.fixture(root,0,1,1);self.fixture(root,1,1)
                self.fixture(root,0,2,**changed)
                with self.assertRaises((ValueError,KeyError)):select(root,Path(d)/'out','tizen',2,'123')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'input';self.fixture(root,0,1)
            with self.assertRaisesRegex(ValueError,'Missing'):select(root,Path(d)/'out','tizen',2,'123')

    def test_incomplete_attempt_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'input';self.fixture(root,0,1);self.fixture(root,1,1)
            (root/'tizen-regression-shard-0-attempt-2').mkdir()
            with self.assertRaisesRegex(ValueError,'Incomplete'):select(root,Path(d)/'out','tizen',2,'123')

    def test_setup_failure_can_be_superseded_by_complete_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'input';self.fixture(root,0,2);self.fixture(root,1,1)
            failed=root/'tizen-regression-shard-0-attempt-1';failed.mkdir()
            (failed/'setup-error.log').write_text('transient download failure')
            select(root,Path(d)/'out','tizen',2,'123')
            self.assertTrue((failed/'setup-error.log').exists())

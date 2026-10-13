import hashlib,json,tempfile,unittest
from unittest.mock import patch
import full_regression
from pathlib import Path
from full_regression import partition,prepare,merge,render_order

class FullRegression(unittest.TestCase):
    def test_enumeration_preserves_gatekeeper_logic_and_all_assertions(self):
        script='for f in tests/*.sh; do\n  n=$(basename "$f")\n  bash "$f" || exit 1\ndone\n'
        adapted=prepare(script,['tests/a.sh','tests/b.sh'])
        self.assertIn('bash "$f" || exit 1',adapted)
        self.assertIn('echo "inventory $n"',adapted)
        with self.assertRaises(ValueError):prepare(script.replace('tests/*.sh','other/*.sh'),[])
    def test_partitions_cover_each_test_exactly_once(self):
        files=['tests/'+str(i)+'.sh' for i in range(577)]
        shards=[partition(files,i,8) for i in range(8)]
        self.assertEqual(sorted(sum(shards,[])),sorted(files))
        self.assertEqual(len(set(sum(shards,[]))),len(files))
        # The long all-scenario benchmark has its own identical Linux host.
        # Nothing is omitted, split into fewer frames, or moved off macOS.
        ten=[partition(files,i,10) for i in range(10)]
        self.assertEqual(sorted(sum(ten,[])),sorted(files))
        self.assertEqual(len(set(sum(ten,[]))),len(files))
        self.assertEqual(ten[9],['tests/fluidez_perf.sh'] if 'tests/fluidez_perf.sh' in files else [])
        self.assertEqual(ten[:8],[partition(files,i,9) for i in range(8)])
        rendering=['tests/fluidez_perf.sh','tests/ui_profile.sh','tests/ilha_voo_cw.sh',
                   'tests/salvospainel.sh','tests/spainel_fundo_tempo.sh','tests/mipcpu.sh',
                   'tests/streamfit_paralelo.sh','tests/tizen-globalthis.sh',
                   'tests/montagem_cedo.sh','tests/home_progressiva.sh','tests/proxyts.sh',
                   'tests/tpk_lifecycle.sh','tests/dts_engine.sh']
        files+=rendering
        shards=[partition(files,i,9) for i in range(9)]
        self.assertEqual(sorted(sum(shards,[])),sorted(files))
        self.assertEqual(shards[8],sorted(rendering,key=render_order))
        self.assertEqual(len(set(sum(shards,[]))),len(files))
        ten=[partition(files,i,10) for i in range(10)]
        self.assertEqual(ten[:8],shards[:8])
        self.assertEqual(ten[9],['tests/fluidez_perf.sh'])
        self.assertEqual(ten[8],sorted(set(rendering)-{'tests/fluidez_perf.sh'},key=render_order))
        self.assertEqual(sorted(sum(ten,[])),sorted(files))
        self.assertEqual(len(set(sum(ten,[]))),len(files))
    def test_balancing_spreads_expensive_fixtures_without_changing_hosts(self):
        files=['tests/f%03d.sh'%i for i in range(64)]
        weights={f:10.0 for f in files}
        for i in (0,8,16,24):weights[files[i]]=1000.0
        special=['tests/fluidez_perf.sh','tests/dts_engine.sh','tests/ui_profile.sh']
        with patch('full_regression.timing_profile',return_value=(weights,25.0,'profile')):
            shards=[partition(files+special,i,10) for i in range(10)]
            self.assertEqual(sorted(sum(shards,[])),sorted(files+special))
            self.assertEqual(len(set(sum(shards,[]))),len(files+special))
            self.assertEqual(shards[9],['tests/fluidez_perf.sh'])
            self.assertEqual(set(shards[8]),set(special)-{'tests/fluidez_perf.sh'})
            loads=[sum(weights[f] for f in group) for group in shards[:8]]
            old=[sum(weights[f] for f in sorted(files)[i::8]) for i in range(8)]
            self.assertLess(max(loads),max(old))
            self.assertEqual(shards,[partition(list(reversed(files+special)),i,10) for i in range(10)])
            unknown=files+['tests/new_fixture.sh']
            self.assertEqual(sorted(sum([partition(unknown,i,10) for i in range(10)],[])),sorted(unknown))

    def test_timing_profiles_fail_closed_on_invalid_durations(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'timings.json'
            with patch('full_regression.PROFILE_PATH',p):
                for duration in (-1,float('nan'),float('inf'),True,'fast'):
                    p.write_text(json.dumps({'schema':1,'seconds':{'tests/a.sh':duration},'unmeasured_seconds':10}))
                    full_regression.timing_profile.cache_clear()
                    with self.subTest(duration=duration),self.assertRaises(ValueError):full_regression.timing_profile()
                p.unlink();full_regression.timing_profile.cache_clear()
                self.assertIsNone(full_regression.timing_profile())
            full_regression.timing_profile.cache_clear()

    def test_merge_binds_balanced_execution_to_the_exact_profile(self):
        files=sorted(['tests/a.sh','tests/mdblist_settings_defaults.sh','tests/fluidez_perf.sh'])
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for index in range(10):
                p=root/f'shard-{index}';p.mkdir();selected=partition(files,index,10)
                text=''.join('inventory '+Path(f).name+'\nok    '+Path(f).name+'\n' for f in selected)
                text+='testes: %d passaram, 0 falharam, 0 SKIP sem prova, 0 fora da suite\n'%len(selected)
                (p/'SUMMARY.txt').write_text(text)
                meta={'index':index,'count':10,'files':files,'selected':selected,'exit_code':0,
                      'gatekeeper_sha256':'same','summary_sha256':hashlib.sha256((p/'SUMMARY.txt').read_bytes()).hexdigest(),
                      'partition_profile_sha256':full_regression.partition_profile_sha256(10),
                      'state':{'upstream_commit':'u','builder_commit':'b','integration':{'fingerprint':'f'}}}
                (p/'execution.json').write_text(json.dumps(meta))
            merge(root,root/'state',root/'summary',10)
            p=root/'shard-9/execution.json';meta=json.loads(p.read_text());meta['partition_profile_sha256']='different'
            p.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,'timing profile mismatch'):merge(root,root/'state',root/'summary',10)

    def test_merge_rejects_missing_execution_or_inconsistent_identity(self):
        files=['tests/a.sh','tests/mdblist_settings_defaults.sh']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for index in range(2):
                p=root/f'shard-{index}';p.mkdir();selected=partition(files,index,2)
                text='inventory '+Path(selected[0]).name+'\nok    '+Path(selected[0]).name+'\ntestes: 1 passaram, 0 falharam, 0 SKIP sem prova, 0 fora da suite\n'
                (p/'SUMMARY.txt').write_text(text)
                meta={'index':index,'count':2,'files':files,'selected':selected,'exit_code':0,
                      'gatekeeper_sha256':'same','summary_sha256':hashlib.sha256((p/'SUMMARY.txt').read_bytes()).hexdigest(),
                      'state':{'upstream_commit':'u','builder_commit':'b','integration':{'fingerprint':'f'}}}
                (p/'execution.json').write_text(json.dumps(meta))
            merge(root,root/'state',root/'summary',2)
            self.assertIn('testes: 2 passaram',(root/'summary').read_text())
            p=root/'shard-1/execution.json';meta=json.loads(p.read_text())
            for field,value in [('selected',[]),('exit_code',1),('state',{'upstream_commit':'different'})]:
                bad={**meta,field:value};p.write_text(json.dumps(bad))
                with self.subTest(field=field),self.assertRaises(ValueError):merge(root,root/'state',root/'summary',2)

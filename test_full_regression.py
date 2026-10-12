import hashlib,json,tempfile,unittest
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

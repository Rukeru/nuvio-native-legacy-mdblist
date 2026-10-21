import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
from full_regression import partition,prepare,merge,render_order,classify,run

GATEKEEPER='''#!/bin/bash
cd "$(dirname "$0")/.."
p=0; x=0
for f in tests/*.sh; do
  n=$(basename "$f")
  if bash "$f" >/dev/null 2>&1; then echo "ok    $n"; p=$((p+1)); else echo "FALHA $n"; x=$((x+1)); fi
done
echo "testes: $p passaram, $x falharam, 0 SKIP sem prova, 0 fora da suite; logs: x"
[ "$x" = 0 ]
'''

def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True,text=True).stdout.strip()

def release(root,scripts):
    """Upstream release commit plus a staged integration on top, like integration.py."""
    (root/'tests').mkdir(parents=True);(root/'tools').mkdir()
    (root/'tools/testa-tudo.sh').write_text(GATEKEEPER,newline='\n')
    for name,code in scripts.items():(root/'tests'/name).write_text('exit %d\n'%code,newline='\n')
    git(root.parent,'init','-q',str(root))
    git(root,'-c','user.email=t@t','-c','user.name=t','add','-A')
    git(root,'-c','user.email=t@t','-c','user.name=t','commit','-qm','release')
    return git(root,'rev-parse','HEAD')

class FullRegression(unittest.TestCase):
    def test_enumeration_preserves_gatekeeper_logic_and_all_assertions(self):
        script='for f in tests/*.sh; do\n  n=$(basename "$f")\n  bash "$f" || exit 1\ndone\n'
        adapted=prepare(script,['tests/a.sh','tests/b.sh'])
        self.assertIn('bash "$f" || exit 1',adapted)
        self.assertIn('echo "inventory $n"',adapted)
        with self.assertRaises(ValueError):prepare(script.replace('tests/*.sh','other/*.sh'),[])
    def test_emulator_artifact_is_checked_once_on_linux(self):
        files=['tests/tpk_x64.sh','tests/fluidez_perf.sh','tests/ordinary.sh']
        shards=[partition(files,i,10) for i in range(10)]
        self.assertIn('tests/tpk_x64.sh',shards[8])
        self.assertNotIn('tests/tpk_x64.sh',sum(shards[:8],[]))
        self.assertEqual(sorted(sum(shards,[])),sorted(files))

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

class UpstreamComparison(unittest.TestCase):
    def test_classify_inherits_only_failures_upstream_ships_and_reproduces(self):
        upstream='FALHA a.sh\nok    b.sh\nSKIP  c.sh (NAO verificado: x)\n'
        inherited,regressions=classify(['a.sh','b.sh','c.sh','own.sh'],upstream,{'a.sh','b.sh','c.sh'})
        self.assertEqual(inherited,['a.sh','c.sh'])
        self.assertEqual(regressions,['b.sh','own.sh'])

    def shard(self,d,integrated):
        root=Path(d)/'upstream';commit=release(root,{'old.sh':1,'fine.sh':0,'mine.sh':0})
        for name,code in integrated.items():(root/'tests'/name).write_text('exit %d\n'%code,newline='\n')
        git(root,'add','-A')
        state=Path(d)/'state.json';state.write_text(json.dumps({'upstream_commit':commit}))
        cwd=os.getcwd();os.chdir(d)
        try:
            with mock.patch('full_regression.environment',return_value={'os':'test'}):run(root,state,0,1)
        finally:os.chdir(cwd)
        return json.loads((Path(d)/'regression-logs/shard-0/execution.json').read_text())

    def test_failure_shared_with_unmodified_upstream_does_not_fail_the_shard(self):
        with tempfile.TemporaryDirectory() as d:
            meta=self.shard(d,{'own.sh':0})
            self.assertEqual(meta['exit_code'],0)
            self.assertEqual(meta['upstream_comparison']['inherited'],['old.sh'])
            self.assertEqual(meta['upstream_comparison']['regressions'],[])
            # The integrated tree still carries its own changes after the comparison.
            self.assertTrue((Path(d)/'upstream/tests/own.sh').is_file())
            self.assertFalse((Path(d)/'upstream-pristine/tests/own.sh').exists())

    def test_failure_that_passes_on_upstream_still_fails_the_shard(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'failed'):self.shard(d,{'mine.sh':1})
            meta=json.loads((Path(d)/'regression-logs/shard-0/execution.json').read_text())
            self.assertEqual(meta['upstream_comparison']['regressions'],['mine.sh'])
            self.assertNotEqual(meta['exit_code'],0)

    def test_failing_script_that_upstream_does_not_ship_still_fails_the_shard(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'failed'):self.shard(d,{'own.sh':1})
            meta=json.loads((Path(d)/'regression-logs/shard-0/execution.json').read_text())
            self.assertEqual(meta['upstream_comparison']['regressions'],['own.sh'])

    def test_merge_accepts_only_reproduced_upstream_failures(self):
        files=['tests/a.sh','tests/old.sh']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'sel';p=root/'shard-0';p.mkdir(parents=True)
            (p/'SUMMARY.txt').write_text('inventory a.sh\nok    a.sh\ninventory old.sh\nFALHA old.sh\ntestes: 1 passaram, 1 falharam, 0 SKIP sem prova, 0 fora da suite\n')
            (p/'UPSTREAM-SUMMARY.txt').write_text('inventory old.sh\nFALHA old.sh\n')
            def write(**change):
                comparison={'commit':'u','failed':['old.sh'],'inherited':['old.sh'],'regressions':[],
                            'summary_sha256':hashlib.sha256((p/'UPSTREAM-SUMMARY.txt').read_bytes()).hexdigest(),**change}
                meta={'index':0,'count':1,'files':files,'selected':files,'exit_code':0,'gatekeeper_sha256':'g',
                      'summary_sha256':hashlib.sha256((p/'SUMMARY.txt').read_bytes()).hexdigest(),
                      'state':{'upstream_commit':'u','builder_commit':'b','integration':{'fingerprint':'f'}},
                      'upstream_comparison':comparison}
                (p/'execution.json').write_text(json.dumps(meta))
            write();merge(root,Path(d)/'state',Path(d)/'summary',1)
            self.assertIn('herdadas do upstream: 1 (old.sh)',(Path(d)/'summary').read_text())
            for change in ({'regressions':['old.sh']},{'inherited':[]},{'commit':'other'},{'summary_sha256':'0'}):
                write(**change)
                with self.subTest(change=change),self.assertRaises(ValueError):merge(root,Path(d)/'state',Path(d)/'summary',1)
            write();(p/'UPSTREAM-SUMMARY.txt').write_text('inventory old.sh\nok    old.sh\n')
            write()
            with self.assertRaises(ValueError):merge(root,Path(d)/'state',Path(d)/'summary',1)

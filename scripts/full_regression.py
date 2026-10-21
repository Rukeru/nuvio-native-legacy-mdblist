"""Partition the upstream gatekeeper across isolated native runners.

Only the gatekeeper's file enumeration is adapted. Reviewed fixture preconditions
are tracked by the integration registry; original assertions, exit rules,
SKIP classification and upstream exclusions are retained.

A script that fails or SKIPs on the integrated tree is rerun, on the same runner,
on the unmodified upstream release. Only failures that upstream shares are
inherited; anything that passes upstream, or that upstream does not ship, still
fails the shard.
"""
from pathlib import Path
import hashlib,json,os,re,shlex,subprocess,sys,threading,time,platform

def environment():
    # Retry reuse is strict about compiler/dependency versions as well as source.
    compiler=os.environ.get('NV_REAL_CC','cc')
    commands=[[compiler,'--version']]
    if sys.platform=='darwin':commands.append(['brew','list','--versions'])
    elif sys.platform.startswith('linux'):commands.append(['dpkg-query','-W'])
    if os.environ.get('NUVIO_DOTNET'):commands.append([os.environ['NUVIO_DOTNET'],'--version'])
    versions=[subprocess.check_output(command,text=True,stderr=subprocess.STDOUT) for command in commands]
    return {'os':platform.system(),'architecture':platform.machine(),
            'runner_image':os.environ.get('ImageOS'),'image_version':os.environ.get('ImageVersion'),
            'python':platform.python_version(),'toolchain_sha256':hashlib.sha256(json.dumps(versions).encode()).hexdigest()}

def partition(files,index,count):
    if count < 1 or not 0 <= index < count:raise ValueError('Invalid regression shard')
    if count in (9,10):
        # Run every frame/scenario of the benchmark on the supported GLES host,
        # including the renderer fixture that is unavailable on macOS.
        rendering={'tests/fluidez_perf.sh','tests/ui_profile.sh','tests/ilha_voo_cw.sh',
                   'tests/salvospainel.sh','tests/spainel_fundo_tempo.sh','tests/mipcpu.sh',
                   'tests/streamfit_paralelo.sh','tests/tizen-globalthis.sh',
                   'tests/montagem_cedo.sh','tests/home_progressiva.sh','tests/proxyts.sh',
                   'tests/tpk_lifecycle.sh','tests/dts_engine.sh','tests/tpk_x64.sh'}
        if count==10:
            if index==9:return sorted(set(files)&{'tests/fluidez_perf.sh'})
            if index==8:return sorted((set(files)&rendering)-{'tests/fluidez_perf.sh'},key=render_order)
        elif index==8:return sorted(set(files)&rendering,key=render_order)
        return sorted(set(files)-rendering)[index::8]
    return sorted(files)[index::count]

def render_order(path):
    # Finish the fast assertions before the full WASM build and all-scenario
    # performance measurement. Every script and every original frame still runs.
    return (2 if path=='tests/fluidez_perf.sh' else 1 if path=='tests/tizen-globalthis.sh' else 0,path)

def prepare(script,selected):
    loop='for f in tests/*.sh; do'
    name='  n=$(basename "$f")'
    if script.count(loop)!=1 or script.count(name)!=1:
        raise ValueError('Upstream full-suite enumeration changed; adapt the runner contract')
    return script.replace(loop,'for f in '+' '.join(shlex.quote(f) for f in selected)+'; do').replace(
        name,name+'\n  echo "inventory $n"')

NOT_OK=re.compile(r'^(?:FALHA|SKIP) +(\S+\.sh)\b',re.M)
OK=re.compile(r'^ok +(\S+\.sh)\s*$',re.M)

def gatekeeper(script,log):
    """Run one prepared gatekeeper, mirroring its output; return (exit, timings)."""
    timings=[];current=None
    process=subprocess.Popen(['bash',str(script)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    for line in process.stdout:
        if line.startswith('inventory '):
            now=time.monotonic()
            if current:timings.append({'script':current[0],'seconds':now-current[1]})
            current=(line.strip().split(' ',1)[1],now)
        log.write(line);log.flush();print(line,end='',flush=True)
    code=process.wait()
    if current:timings.append({'script':current[0],'seconds':time.monotonic()-current[1]})
    return code,timings

def classify(failed,upstream_text,shipped):
    """Split integrated failures into those upstream shares and real regressions."""
    passed=set(OK.findall(upstream_text));not_ok=set(NOT_OK.findall(upstream_text))
    inherited=[n for n in failed if n in shipped and n in not_ok and n not in passed]
    return inherited,[n for n in failed if n not in inherited]

def compare_upstream(root,state,failed,evidence):
    commit=state.get('upstream_commit')
    if not commit or not re.fullmatch(r'[0-9a-f]{40}',commit):raise ValueError('Tested upstream commit unknown; cannot compare failures')
    pristine=root.parent/(root.name+'-pristine')
    if pristine.exists():raise ValueError('Pristine upstream checkout already exists; use a fresh runner')
    subprocess.run(['git','-C',str(root),'worktree','add','--detach',str(pristine),commit],check=True)
    if subprocess.check_output(['git','-C',str(pristine),'rev-parse','HEAD'],text=True).strip()!=commit:
        raise ValueError('Pristine upstream checkout is not the tested release')
    if subprocess.check_output(['git','-C',str(pristine),'status','--porcelain'],text=True).strip():
        raise ValueError('Pristine upstream checkout is modified')
    shipped={n for n in failed if (pristine/'tests'/n).is_file()}
    summary=evidence/'UPSTREAM-SUMMARY.txt'
    code=0
    with summary.open('w',encoding='utf8') as log:
        if shipped:
            original=(pristine/'tools/testa-tudo.sh').read_text()
            script=pristine/'tools/.ci-full-regression.sh'
            script.write_text(prepare(original,['tests/'+n for n in failed if n in shipped]),encoding='utf8')
            print(f'::group::Same failing scripts on unmodified upstream {commit[:12]}',flush=True)
            code,_=gatekeeper(script,log)
            print('::endgroup::',flush=True)
    inherited,regressions=classify(failed,summary.read_text(),shipped)
    for name in inherited:print(f'inherited from upstream {commit[:12]}: {name} fails there too',flush=True)
    for name in regressions:
        print(f'::error::{name} fails here but '+('passes on' if name in shipped else 'is not shipped by')+f' upstream {commit[:12]}',flush=True)
    return {'commit':commit,'failed':failed,'inherited':inherited,'regressions':regressions,
            'gatekeeper_exit_code':code,'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest()}

def run(root,state_path,index,count):
    root=Path(root).resolve();state_path=Path(state_path).resolve()
    files=sorted(p.relative_to(root).as_posix() for p in (root/'tests').glob('*.sh'))
    if not files:raise ValueError('No upstream regression scripts found')
    selected=partition(files,index,count)
    original=(root/'tools/testa-tudo.sh').read_text()
    script=root/'tools/.ci-full-regression.sh';script.write_text(prepare(original,selected),encoding='utf8')
    evidence=Path(f'regression-logs/shard-{index}');evidence.mkdir(parents=True,exist_ok=True)
    summary=evidence/'SUMMARY.txt'
    stop=threading.Event()
    def progress():
        # The upstream gatekeeper buffers individual fixture output. Report
        # growth without changing its assertions, exit rules or coverage.
        previous={}
        folder=Path(os.environ.get('TMPDIR','/tmp'))
        while not stop.wait(30):
            for path in folder.glob('nuvio-testes.*/*.log'):
                try:
                    size=path.stat().st_size
                    if previous.get(str(path))!=size:
                        print(f'[fixture progress] {path.name}: {size} log bytes',flush=True)
                        previous[str(path)]=size
                except OSError:pass
    observer=threading.Thread(target=progress,daemon=True);observer.start()
    started=time.monotonic()
    with summary.open('w',encoding='utf8') as log:code,timings=gatekeeper(script,log)
    state=json.loads(state_path.read_text())
    text=summary.read_text()
    result=re.search(r'testes: (\d+) passaram, (\d+) falharam, (\d+) SKIP sem prova, (\d+) fora da suite',text)
    gate_code=code;comparison=None
    failed=NOT_OK.findall(text)
    try:
        if failed:comparison=compare_upstream(root,state,failed,evidence)
    finally:stop.set();observer.join()
    if not result or int(result.group(2)) or int(result.group(3)):code=code or 1
    # Exactly the failures that unmodified upstream shares, and nothing else.
    if (code and result and comparison and not comparison['regressions']
            and int(result.group(2))+int(result.group(3))==len(failed)==len(comparison['inherited'])):code=0
    metadata={'index':index,'count':count,'files':files,'selected':selected,'exit_code':code,'gatekeeper_exit_code':gate_code,
              'gatekeeper_sha256':hashlib.sha256(original.encode()).hexdigest(),
              'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'state':state,
              'run_id':os.environ.get('GITHUB_RUN_ID','local'),
              'attempt':int(os.environ.get('GITHUB_RUN_ATTEMPT','1')),
              'environment':environment(),
              'seconds':time.monotonic()-started,'timings':timings}
    if comparison:metadata['upstream_comparison']=comparison
    (evidence/'execution.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
    if code:raise RuntimeError(f'Full regression shard {index} failed; see its complete logs')

def merge(folder,state_out,summary_out,count):
    folder=Path(folder);seen=[];results=[];baseline=None;total=[0,0,0,0];herdadas=[]
    for index in range(count):
        p=folder/f'shard-{index}';meta=json.loads((p/'execution.json').read_text());summary=(p/'SUMMARY.txt').read_text()
        if meta['index']!=index or meta['count']!=count or meta['exit_code']!=0:
            raise ValueError(f'Missing or unsuccessful regression shard {index}')
        if hashlib.sha256((p/'SUMMARY.txt').read_bytes()).hexdigest()!=meta['summary_sha256']:
            raise ValueError('Regression summary checksum mismatch')
        identity=(meta['state'].get('upstream_commit'),meta['state'].get('builder_commit'),
                  meta['state'].get('integration',{}).get('fingerprint'),meta['gatekeeper_sha256'],meta['files'])
        if baseline is None:baseline=identity;state=meta['state']
        elif identity!=baseline:raise ValueError('Regression shards tested different sources or inventories')
        expected=partition(meta['files'],index,count)
        observed=['tests/'+name for name in re.findall(r'^inventory (.+)$',summary,re.M)]
        if meta['selected']!=expected or observed!=expected:
            raise ValueError('Regression shard omitted, duplicated or substituted a test script')
        match=re.search(r'testes: (\d+) passaram, (\d+) falharam, (\d+) SKIP sem prova, (\d+) fora da suite',summary)
        if not match:raise ValueError('Regression shard result missing')
        numbers=list(map(int,match.groups()))
        failing=NOT_OK.findall(summary);comparison=meta.get('upstream_comparison')
        if failing:
            # Accept only failures that the same runner reproduced on unmodified upstream.
            upstream=p/'UPSTREAM-SUMMARY.txt'
            if not comparison or comparison.get('regressions') or comparison.get('failed')!=failing:
                raise ValueError(f'Regression shard {index} has failures that unmodified upstream does not share')
            if comparison.get('commit')!=meta['state'].get('upstream_commit'):raise ValueError('Upstream comparison tested a different release')
            if not upstream.is_file() or hashlib.sha256(upstream.read_bytes()).hexdigest()!=comparison.get('summary_sha256'):
                raise ValueError('Upstream comparison summary checksum mismatch')
            inherited,regressions=classify(failing,upstream.read_text(),set(failing))
            if regressions or inherited!=comparison.get('inherited'):raise ValueError('Upstream comparison does not reproduce every failure')
            herdadas+=inherited
        elif comparison:raise ValueError('Upstream comparison without integrated failures')
        if numbers[1]+numbers[2]!=len(failing) or sum(numbers)!=len(expected):raise ValueError('Regression shard result does not cover its entire inventory')
        total=[a+b for a,b in zip(total,numbers)];seen+=observed
        # Keep each original result line, with one aggregate result at the end.
        results.append(re.sub(r'^testes: .*$',f'shard {index}: '+match.group(0),summary,flags=re.M))
    if sorted(seen)!=baseline[-1] or len(set(seen))!=len(seen):raise ValueError('Full regression coverage is incomplete')
    result='\n'.join(results)+'\n'+'testes: %d passaram, %d falharam, %d SKIP sem prova, %d fora da suite; isolated native runners\n'%tuple(total)
    result+='herdadas do upstream: %d%s\n'%(len(herdadas),(' ('+' '.join(sorted(herdadas))+')') if herdadas else '')
    Path(state_out).write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    Path(summary_out).write_text(result,encoding='utf8')
    print(result.splitlines()[-1])

if __name__=='__main__':
    if len(sys.argv)==6 and sys.argv[1]=='run':run(sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]))
    elif len(sys.argv)==6 and sys.argv[1]=='merge':merge(sys.argv[2],sys.argv[3],sys.argv[4],int(sys.argv[5]))
    else:raise SystemExit('Usage: full_regression.py run ROOT STATE INDEX COUNT | merge FOLDER STATE SUMMARY COUNT')

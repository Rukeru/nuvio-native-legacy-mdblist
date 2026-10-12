"""Partition the unchanged upstream gatekeeper across isolated native runners.

Only its file enumeration is adapted. Test scripts, assertions, exit rules,
SKIP classification and upstream exclusions remain upstream-owned.
"""
from pathlib import Path
import hashlib,json,re,shlex,subprocess,sys

def partition(files,index,count):
    if count < 1 or not 0 <= index < count:raise ValueError('Invalid regression shard')
    return sorted(files)[index::count]

def prepare(script,selected):
    loop='for f in tests/*.sh; do'
    name='  n=$(basename "$f")'
    if script.count(loop)!=1 or script.count(name)!=1:
        raise ValueError('Upstream full-suite enumeration changed; adapt the runner contract')
    return script.replace(loop,'for f in '+' '.join(shlex.quote(f) for f in selected)+'; do').replace(
        name,name+'\n  echo "inventory $n"')

def run(root,state_path,index,count):
    root=Path(root).resolve();state_path=Path(state_path).resolve()
    files=sorted(p.relative_to(root).as_posix() for p in (root/'tests').glob('*.sh'))
    if not files:raise ValueError('No upstream regression scripts found')
    selected=partition(files,index,count)
    original=(root/'tools/testa-tudo.sh').read_text()
    script=root/'tools/.ci-full-regression.sh';script.write_text(prepare(original,selected),encoding='utf8')
    evidence=Path(f'regression-logs/shard-{index}');evidence.mkdir(parents=True,exist_ok=True)
    summary=evidence/'SUMMARY.txt'
    with summary.open('w',encoding='utf8') as log:
        process=subprocess.Popen(['bash',str(script)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:
            log.write(line);log.flush();print(line,end='',flush=True)
        code=process.wait()
    state=json.loads(state_path.read_text())
    metadata={'index':index,'count':count,'files':files,'selected':selected,'exit_code':code,
              'gatekeeper_sha256':hashlib.sha256(original.encode()).hexdigest(),
              'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'state':state}
    (evidence/'execution.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
    if code:raise RuntimeError(f'Full regression shard {index} failed; see its complete logs')

def merge(folder,state_out,summary_out,count):
    folder=Path(folder);seen=[];results=[];baseline=None;total=[0,0,0,0]
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
        if numbers[1] or sum(numbers)!=len(expected):raise ValueError('Regression shard result does not cover its entire inventory')
        total=[a+b for a,b in zip(total,numbers)];seen+=observed
        # Keep each original result line, with one aggregate result at the end.
        results.append(re.sub(r'^testes: .*$',f'shard {index}: '+match.group(0),summary,flags=re.M))
    if sorted(seen)!=baseline[-1] or len(set(seen))!=len(seen):raise ValueError('Full regression coverage is incomplete')
    result='\n'.join(results)+'\n'+'testes: %d passaram, %d falharam, %d SKIP sem prova, %d fora da suite; isolated native runners\n'%tuple(total)
    Path(state_out).write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    Path(summary_out).write_text(result,encoding='utf8')
    print(result.splitlines()[-1])

if __name__=='__main__':
    if len(sys.argv)==6 and sys.argv[1]=='run':run(sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]))
    elif len(sys.argv)==6 and sys.argv[1]=='merge':merge(sys.argv[2],sys.argv[3],sys.argv[4],int(sys.argv[5]))
    else:raise SystemExit('Usage: full_regression.py run ROOT STATE INDEX COUNT | merge FOLDER STATE SUMMARY COUNT')

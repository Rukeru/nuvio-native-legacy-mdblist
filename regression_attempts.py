"""Select latest shard attempts without merging or overwriting evidence files."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil
from full_regression import merge


def select(folder,output,platform,count,run_id):
    folder=Path(folder);output=Path(output)
    if output.exists():raise ValueError('Attempt selection output must be new')
    candidates={};identity=None;record=[]
    pattern=re.compile(re.escape(platform)+r'-regression-shard-(\d+)-attempt-(\d+)')
    for artifact in sorted(folder.iterdir()):
        match=pattern.fullmatch(artifact.name)
        if not match:raise ValueError('Unexpected regression artifact: '+artifact.name)
        index,attempt=map(int,match.groups())
        if not 0<=index<count or attempt<1:raise ValueError('Invalid shard attempt')
        meta_path=artifact/'regression-logs'/f'shard-{index}'/'execution.json'
        # Incomplete attempts must not silently fall back to an earlier result.
        if not meta_path.is_file():raise ValueError('Incomplete regression attempt: '+artifact.name)
        meta=json.loads(meta_path.read_text())
        if (meta.get('index'),meta.get('count'),meta.get('attempt'),meta.get('run_id'))!=(index,count,attempt,str(run_id)):
            raise ValueError('Regression attempt provenance mismatch')
        state=meta['state']
        actual=(state.get('upstream_commit'),state.get('builder_commit'),
                state.get('integration',{}).get('fingerprint'),meta['gatekeeper_sha256'],meta['files'])
        if not all(actual):raise ValueError('Incomplete source identity')
        if identity is None:identity=actual
        elif actual!=identity:raise ValueError('Regression attempts tested different sources')
        summary=meta_path.with_name('SUMMARY.txt')
        if not summary.is_file() or hashlib.sha256(summary.read_bytes()).hexdigest()!=meta['summary_sha256']:
            raise ValueError('Regression attempt summary checksum mismatch')
        if index in candidates:
            previous=candidates[index][2]
            if previous.get('environment')!=meta.get('environment'):
                raise ValueError('Retry environment changed; new complete validation is required')
        if not meta.get('environment'):raise ValueError('Regression environment evidence missing')
        if index not in candidates or attempt>candidates[index][0]:
            candidates[index]=(attempt,meta_path.parent,meta)
        record.append({'artifact':artifact.name,'execution_sha256':hashlib.sha256(meta_path.read_bytes()).hexdigest(),
                       'exit_code':meta['exit_code']})
    if set(candidates)!=set(range(count)):raise ValueError('Missing required regression shards')
    if any(meta['exit_code']!=0 for _,_,meta in candidates.values()):
        raise ValueError('Latest regression attempt failed; prior success cannot replace it')
    output.mkdir(parents=True)
    for index,(_,path,_) in candidates.items():shutil.copytree(path,output/f'shard-{index}')
    (output/'ATTEMPTS.json').write_text(json.dumps({'run_id':str(run_id),
        'selected':{str(index):value[0] for index,value in candidates.items()},'retained':record},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('folder','output','platform'):parser.add_argument(name)
    parser.add_argument('count',type=int);args=parser.parse_args()
    select(args.folder,args.output,args.platform,args.count,os.environ['GITHUB_RUN_ID'])

"""Compare the same complete fixture assertions with the original/cached driver.

This diagnostic does not attest or authorize any application release.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,time


def run(root,fixtures,out,mode):
    root=Path(root).resolve();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for fixture in fixtures:
        if not fixture.startswith('tests/') or '..' in Path(fixture).parts or not (root/fixture).is_file():
            raise ValueError('Unknown fixture')
        started=time.monotonic()
        with (out/(Path(fixture).name+'.log')).open('wb') as log:
            process=subprocess.run(['bash',fixture],cwd=root,stdout=log,stderr=subprocess.STDOUT)
        text=(out/(Path(fixture).name+'.log')).read_text(errors='replace')
        import re
        unavailable=bool(re.search(r'(^|[^A-Za-z])SKIP([^A-Za-z]|$)|PULADO|sem resultado',text))
        results.append({'fixture':fixture,'seconds':time.monotonic()-started,
            'exit_code':process.returncode,'unavailable':unavailable,
            'fixture_sha256':hashlib.sha256((root/fixture).read_bytes()).hexdigest()})
        print(mode,results[-1],flush=True)
    (out/'TIMINGS.json').write_text(json.dumps({'diagnostic_only':True,'mode':mode,
        'builder':os.environ.get('GITHUB_SHA'),'results':results},indent=2)+'\n')
    if any(x['exit_code'] or x['unavailable'] for x in results):raise RuntimeError('Focused benchmark fixture did not fully pass')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('out');parser.add_argument('mode')
    parser.add_argument('fixtures',nargs='+');args=parser.parse_args()
    run(args.root,args.fixtures,args.out,args.mode)

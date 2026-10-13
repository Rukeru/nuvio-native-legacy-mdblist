"""Summarize GitHub job/step timestamps without double-counting reused jobs."""
from datetime import datetime
from pathlib import Path
import argparse,json


def seconds(a,b):return max(0,(datetime.fromisoformat(b.replace('Z','+00:00'))-datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds())


def category(name):
    name=name.lower()
    if 'checkout' in name:return 'checkout'
    if 'artifact' in name:return 'artifacts'
    if 'compar' in name and 'render' in name:return 'render_comparison'
    if 'execute the complete' in name:return 'regression_execution'
    if 'aggregate' in name or 'verify every script' in name:return 'aggregation'
    if 'publish' in name:return 'publication'
    if 'compatibility' in name or 'assemble verified' in name or 'interfaces' in name:return 'integration_preflight'
    if name.startswith('build ') and ('native' in name or 'tizen' in name):return 'native_build'
    if 'provision' in name or 'sdk' in name or 'toolchain' in name or 'workload' in name:return 'sdk_and_toolchains'
    if 'install' in name and ('libraries' in name or 'dependencies' in name or 'cli' in name):return 'dependencies'
    if 'build' in name and ('native' in name or 'tizen' in name):return 'native_build'
    return 'other'


def profile(data):
    jobs=[];seen=set();groups={};queue=0;runner=0
    for job in sorted(data['jobs'],key=lambda x:(x['run_attempt'],x['id'])):
        if job['conclusion']=='skipped' or not job.get('started_at') or not job.get('completed_at'):continue
        # GitHub duplicates retained jobs in later attempts, with a new job ID
        # and creation time but the ORIGINAL execution timestamps and steps.
        identity=(job['name'],job['started_at'],job['completed_at'])
        if identity in seen:continue
        seen.add(identity)
        duration=seconds(job['started_at'],job['completed_at']);wait=seconds(job['created_at'],job['started_at'])
        runner+=duration;queue+=wait
        steps=[]
        for step in job['steps']:
            if step['conclusion'] not in ('success','failure'):continue
            elapsed=seconds(step['started_at'],step['completed_at']);group=category(step['name'])
            groups[group]=groups.get(group,0)+elapsed
            steps.append({'name':step['name'],'seconds':elapsed,'category':group})
        jobs.append({'id':job['id'],'name':job['name'],'attempt':job['run_attempt'],
            'conclusion':job['conclusion'],'queue_seconds':wait,'runner_seconds':duration,
            'started_at':job['started_at'],'completed_at':job['completed_at'],'labels':job.get('labels',[]),'steps':steps})
    if not jobs:raise ValueError('No completed execution evidence')
    peaks={}
    for label in {v for j in jobs for v in j['labels']}:
        events=sorted([(j['started_at'],1) for j in jobs if label in j['labels']]+
                      [(j['completed_at'],-1) for j in jobs if label in j['labels']])
        active=peak=0
        for _,delta in events:active+=delta;peak=max(peak,active)
        peaks[label]=peak
    return {'elapsed_seconds':seconds(min(j['started_at'] for j in jobs),max(j['completed_at'] for j in jobs)),
        'runner_seconds':runner,'sum_job_queue_seconds':queue,'stage_runner_seconds':groups,
        'critical_last_job':max(jobs,key=lambda j:j['completed_at'])['name'],
        'observed_peak_runners':peaks,'jobs':jobs,'note':'Queue sum is per-job waiting, not extra wall time; runner time is measured execution, not billed rounded minutes.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input');parser.add_argument('output');args=parser.parse_args()
    result=profile(json.loads(Path(args.input).read_text()))
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='jobs'},indent=2))

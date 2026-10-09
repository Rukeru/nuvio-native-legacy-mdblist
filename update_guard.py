"""Release selection, conflict quarantine, actionable issues and transport retries."""
from pathlib import Path
import argparse, json, os, re, subprocess, time, urllib.request
from resilience import fetch, transient

REPO='Rukeru/nuvio-native-legacy-mdblist'

def api(path, data=None, method=None):
    headers={'User-Agent':'Nuvio-update-guard','Accept':'application/vnd.github+json'}
    if os.environ.get('GH_TOKEN'):headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    if data is not None:headers['Content-Type']='application/json'
    req=urllib.request.Request('https://api.github.com/'+path,
          data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
    # Read operations are idempotent. Mutations use reconciliation in their caller.
    if data is None and method is None:return json.loads(fetch(req))
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def pages(path):
    results=[]
    for page in range(1,101):
        batch=api(path+('&' if '?' in path else '?')+f'per_page=100&page={page}')
        results.extend(batch)
        if len(batch)<100:return results
    raise RuntimeError('Pagination limit exceeded; refusing partial release selection')

def stable(releases,prefix='v'):
    candidates=[]
    for r in releases:
        tag=r.get('tag_name','')
        if r.get('draft') or r.get('prerelease') or not tag.startswith(prefix):continue
        v=tag[len(prefix):]
        if re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?',v):
            candidates.append((tuple(map(int,v.split('.'))),r.get('published_at',''),r.get('id',0),r))
    return max(candidates,key=lambda x:x[:3])[3] if candidates else None

def marker(platform,state):
    from integration import fingerprint
    return '<!-- update-block: '+platform+':'+str(state['upstream']['id'])+':'+fingerprint()+' -->'

def issues():return [i for i in pages('repos/'+REPO+'/issues?state=open') if 'pull_request' not in i]

def blocked(platform,state,force=False):
    if force:return False
    key=marker(platform,state)
    matches=[i for i in issues() if key in (i.get('body') or '')]
    if matches:
        print('Known incompatibility; expensive build skipped:',matches[0]['html_url'])
        summary=os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary,'a') as f:f.write('Known source incompatibility: '+matches[0]['html_url']+'\n\nChange the adapter/contract to retry, or use manual force after investigation. Last published release retained.\n')
        return True
    return False

def network_log(text):
    # Never turn source, linker, assertion or checksum failures into network retries.
    if re.search(r':\d+(?::\d+)?: (?:fatal )?error:|undefined reference|Assertion|checksum mismatch|CONFLICT|patch failed|contract-failure',text,re.I):return False
    return bool(re.search(r'Could not resolve host|Temporary failure resolving|Connection (?:reset|timed out)|TLS connection was non-properly terminated|HTTP(?:/[0-9.]+)? (?:408|429|50[0234])|returned error: (?:408|429|50[0234])|unexpected status from (?:HEAD|GET) request to https://[^\s]+: (?:408|429|50[0234])|connection reset by peer|net/http: TLS handshake timeout|unexpected EOF|failed to fetch.*(?:timeout|503)',text,re.I))

def network_command(command, attempts=3, sleep=time.sleep):
    for n in range(attempts):
        lines=[]
        # Keep Actions diagnostics live during lengthy native builds.
        with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1) as process:
            for line in process.stdout:
                print(line,end='',flush=True);lines.append(line)
            code=process.wait()
        output=''.join(lines)
        if code==0:return
        if not network_log(output) or n+1==attempts:
            raise subprocess.CalledProcessError(code,command,output=output)
        print(f'Transient download failure; retry {n+2}/{attempts}',flush=True);sleep(5*2**n)

def run(platform,state_file,stage,command):
    state=json.loads(Path(state_file).read_text())
    from integration import report
    try:network_command(command)
    except subprocess.CalledProcessError as error:
        kind='transient-failure' if network_log(error.output) else 'check-failure'
        components=re.findall(r'^::integration-component::([^\r\n]+)',error.output,re.M)
        files=sorted(set(re.findall(r'\b((?:src|tests)/[\w./-]+\.(?:c|h|inc|sh|py))(?=[:\s])',error.output)))
        report(platform,state,components[-1] if components else stage,kind,error.output,files)
        raise

def failure(platform,state_file,stage='workflow'):
    from integration import report, ROOT
    state=json.loads(Path(state_file).read_text()) if Path(state_file).exists() else None
    if not state:print('Discovery failed before a release was selected; see Actions log.');return
    path=ROOT/'diagnostics'/f'{platform}-compatibility.json'
    diagnostic=json.loads(path.read_text()) if path.exists() else {}
    if diagnostic.get('status') in ('source-compatible','preflight-passed') or not diagnostic:
        diagnostic=report(platform,state,stage,'build-failure','The named workflow stage failed. Open the run below for exact logs; no release was published.')
    deterministic=diagnostic['status'] in ('source-conflict','contract-failure','check-failure')
    key=marker(platform,state) if deterministic else '<!-- update-failure: '+platform+':'+str(state['upstream']['id'])+' -->'
    body=(key+'\n\nUpstream: **'+state['upstream']['tag_name']+'**\n\nPlatform: **'+platform+'**\n\n'
          'Integration requiring attention: **'+diagnostic['component']+'**\n\n'
          'Status: `'+diagnostic['status']+'`\n\nAffected files: '+', '.join(diagnostic.get('files',[]))+'\n\n'
          'Workflow and full logs: '+diagnostic['run_url']+'\n\n'
          'Last working release has been preserved. '+
          ('This source/check failure is quarantined for this upstream release and integration fingerprint. Adapt the named component, update its reviewed digest/contracts/tests, and push; both monitors will recheck. A different upstream release also rechecks automatically.' if deterministic else 'Transport operations have bounded retries. The next scheduled check may recover; inspect the run if it persists.')+'\n\n'
          '```text\n'+diagnostic.get('details','')[-6000:].replace('```','~~~')+'\n```\n')
    matches=[i for i in issues() if key in (i.get('body') or '')]
    if matches: print('Failure already reported:',matches[0]['html_url']);return
    # A lost POST response must not blindly create duplicate public notifications.
    try:created=api('repos/'+REPO+'/issues',{'title':f'[{platform}] {state["upstream"]["tag_name"]}: adapt {diagnostic["component"]}','body':body})
    except Exception:
        matches=[i for i in issues() if key in (i.get('body') or '')]
        if not matches:raise
        created=matches[0]
    print('Reported update failure:',created['html_url'])

def recovered(platform,state):
    prefix='<!-- update-block: '+platform+':'+str(state['upstream']['id'])+':'
    other='<!-- update-failure: '+platform+':'+str(state['upstream']['id'])+' -->'
    for issue in issues():
        if prefix in (issue.get('body') or '') or other in (issue.get('body') or ''):
            api('repos/'+REPO+'/issues/'+str(issue['number']),{'state':'closed','state_reason':'completed'},'PATCH')

def arguments(argv):
    # REMAINDER after a positional action would consume --platform/--state.
    # Parse our flags before the separator; pass the command unchanged afterward.
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','failure']);p.add_argument('--platform',required=True);p.add_argument('--state',required=True);p.add_argument('--stage',default='workflow')
    split=argv.index('--') if '--' in argv else len(argv)
    a=p.parse_args(argv[:split]);a.command=argv[split+1:]
    return a

if __name__=='__main__':
    import sys
    a=arguments(sys.argv[1:])
    if a.action=='failure':failure(a.platform,a.state,a.stage)
    else:run(a.platform,a.state,a.stage,a.command)

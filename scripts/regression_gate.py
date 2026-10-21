"""Attest real full-suite execution and bind publication to its tested source."""
from pathlib import Path
import hashlib,json,re,sys

def attest(state_path,summary_path):
    text=Path(summary_path).read_text()
    match=re.search(r'^testes: (\d+) passaram, (\d+) falharam, (\d+) SKIP sem prova, (\d+) fora da suite',text,re.M)
    if not match:raise ValueError('Full regression result missing; a skipped workflow is not validation')
    passed,failed,unavailable,outside=map(int,match.groups())
    # merge() lists every failure that unmodified upstream reproduced on the
    # same runner; anything beyond that list is a regression of this build.
    shared=re.search(r'^herdadas do upstream: (\d+)(?: \(([^)]*)\))?$',text,re.M)
    inherited=sorted((shared.group(2) or '').split()) if shared else []
    if shared and int(shared.group(1))!=len(inherited):raise ValueError('Inherited upstream failure list is inconsistent')
    if passed<1 or failed+unavailable!=len(inherited):raise ValueError('Full upstream regression suite did not pass completely')
    if not re.search(r'^ok\s+mdblist_settings_defaults\.sh\s*$',text,re.M):
        raise ValueError('Upstream and MDBList factory-default assertions were not verified')
    state=json.loads(Path(state_path).read_text())
    state['full_regression']={'outcome':'passed','passed':passed,'failed':failed,
        'unavailable':unavailable,'outside_upstream_gatekeeper':outside,'inherited_from_upstream':inherited,
        'summary_sha256':hashlib.sha256(Path(summary_path).read_bytes()).hexdigest()}
    Path(state_path).write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    print('Verified full regression execution:',state['full_regression'])

def validate(state,path='regression-evidence/regression-state.json'):
    tested=json.loads(Path(path).read_text())
    if state.get('diagnostic_only') or tested.get('diagnostic_only'):
        raise ValueError('Diagnostic execution cannot authorize publication')
    for key in ('upstream_commit','builder_commit'):
        if not state.get(key) or state[key]!=tested.get(key):raise ValueError('Regression provenance mismatch: '+key)
    actual=state.get('integration',{}).get('fingerprint')
    if not actual or actual!=tested.get('integration',{}).get('fingerprint'):
        raise ValueError('Regression provenance mismatch: integration fingerprint')
    result=tested.get('full_regression',{})
    inherited=result.get('inherited_from_upstream',[])
    if (result.get('outcome')!='passed' or result.get('passed',0)<1 or not isinstance(result.get('failed'),int)
            or not isinstance(result.get('unavailable'),int) or result['failed']+result['unavailable']!=len(inherited)):
        raise ValueError('No successful full regression execution attested')
    return result

if __name__=='__main__':
    if len(sys.argv)!=4 or sys.argv[1]!='attest':raise SystemExit('Usage: regression_gate.py attest STATE SUMMARY')
    attest(sys.argv[2],sys.argv[3])

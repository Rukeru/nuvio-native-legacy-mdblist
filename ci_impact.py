"""Conservative development gate selection. This never authorizes publication."""
from pathlib import Path
import argparse,json,subprocess

CI_ONLY={'ci_compile.py','ci_benchmark.py','ci_profile.py','ci_impact.py','regression_attempts.py',
         'full_regression.py','regression_gate.py','regression_dependencies.py'}


def classify(paths):
    native=False;compiler=False;backend=False;unknown=[]
    for name in paths:
        p=Path(name)
        if p.suffix=='.md' or name in ('LICENSE','.gitignore','.gitattributes','.channel/last-check.txt') or name.startswith('ci-evidence/'):
            continue
        if name.startswith('test_') and p.suffix=='.py':continue
        if name.startswith('private-diagnostics/') or name=='.github/workflows/diagnostics.yml':
            backend=True;continue
        if name in CI_ONLY or name.startswith('.github/workflows/'):
            compiler |= name in ('ci_compile.py','ci_benchmark.py','.github/workflows/ci-experiment.yml')
            continue
        if name.startswith('integration/') or name.startswith('integration-bundle.') or p.suffix in ('.patch','.py','.sh') or name=='global.json':
            native=True;continue
        unknown.append(name)
    if unknown:raise ValueError('Unclassified change: extend the reviewed impact map before validation: '+', '.join(unknown))
    return {'release_validation':False,'unit_tests':'all test_*.py',
            'native_platforms':['tizen','webos'] if native else [],
            'compiler_equivalence_required':compiler,
            'backend_security_required':backend,
            'native_gate':['integration contracts','preflight.sh','platform-checks.sh','focused-ui.yml'] if native else [],
            'full_release_required_before_publication':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--head',default='HEAD')
    parser.add_argument('--output',default='development-impact.json');args=parser.parse_args()
    paths=subprocess.check_output(['git','diff','--name-only',args.base,args.head,'--'],text=True).splitlines()
    result=classify(paths);result['changed_paths']=paths
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    import os
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            f.write('native='+str(bool(result['native_platforms'])).lower()+'\n')
            f.write('compiler='+str(result['compiler_equivalence_required']).lower()+'\n')
            f.write('backend='+str(result['backend_security_required']).lower()+'\n')
    print(json.dumps(result,indent=2))

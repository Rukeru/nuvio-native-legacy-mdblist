"""Compare real GLES UI against the first build and 2.0.2.11, without user data."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tarfile, tempfile, urllib.request

REPO='https://api.github.com/repos/Rukeru/nuvio-native-legacy-mdblist'
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Nuvio-public-UI-profile'}),timeout=180) as reply:
        return reply.read()
def changelog_only(current):
    # Reuse the completed rendering comparison only for this exact additive UI
    # patch, with identical upstream and all previous patch digests. An upstream
    # change or another custom patch always runs the full comparison below.
    try:
        state_path=Path('state.json')
        if not state_path.is_file(): return None
        state=json.loads(state_path.read_text())
        patches=state.get('tizen_improvements', [])
        if len(patches)<3 or [p['patch'] for p in patches[-3:]]!=[
                'shared-09-installed-changelog.patch','shared-10-changelog-modal-guards.patch',
                'shared-11-changelog-readability.patch']: return None
        release=json.loads(fetch(REPO+'/releases/latest'))
        asset=next(a for a in release['assets'] if a['name']=='SOURCE.json')
        data=fetch(asset['browser_download_url'])
        if asset.get('digest')!='sha256:'+hashlib.sha256(data).hexdigest(): return None
        previous=json.loads(data)
        if previous.get('upstream_commit')!=state.get('upstream_commit'): return None
        if previous.get('tizen_improvements') not in (patches[:-3], patches[:-2], patches[:-1], patches): return None
        return release['html_url']
    except (ValueError, KeyError, StopIteration, OSError):
        return None
def run(current,out):
    current=Path(current).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    evidence={'hardware':'GitHub Linux runner / Mesa software GLES2; not a TV','baselines':[]}
    inherited=changelog_only(current)
    if inherited:
        print('UI-profile: installed changelog; unchanged rendering comparison from '+inherited,flush=True)
        subprocess.run(['bash',str(current/'tests/ui_profile.sh'),str(current),str(out/'current')],
                       env={**os.environ,'NV_CHANGELOG_ONLY':'1'},check=True)
        evidence.update({'rendering_comparison_inherited_from':inherited,'new_scene':'installed update changelog'})
        (out/'PROVENANCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
        return
    with tempfile.TemporaryDirectory(prefix='nuvio-ui-profile-') as temp:
        temp=Path(temp)
        print('UI-profile: current production and cache experiment',flush=True)
        subprocess.run(['bash',str(current/'tests/ui_profile.sh'),str(current),str(out/'current')],check=True)
        for tag in ('v2.0.2.3','v2.0.2.11'):
            print('UI-profile: published baseline '+tag,flush=True)
            release=json.loads(fetch(REPO+'/releases/tags/'+tag))
            asset=next(a for a in release['assets'] if a['name'].startswith('source-') and a['name'].endswith('.tar.gz'))
            data=fetch(asset['browser_download_url']);sha=hashlib.sha256(data).hexdigest()
            if asset.get('digest')!='sha256:'+sha:raise RuntimeError('Public baseline source digest mismatch')
            archive=temp/(tag+'.tar.gz');archive.write_bytes(data)
            checkout=temp/tag;checkout.mkdir()
            with tarfile.open(archive) as packed:packed.extractall(checkout,filter='data')
            tree=next(p.parent for p in checkout.rglob('src') if p.is_dir() and (p/'home.c').is_file())
            subprocess.run(['bash',str(current/'tests/ui_profile.sh'),str(tree),str(out/tag)],check=True)
            evidence['baselines'].append({'tag':tag,'source_sha256':sha,'release':release['html_url']})
    (out/'PROVENANCE.json').write_text(json.dumps(evidence,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--current',default='upstream');parser.add_argument('--out',default='ui-profile')
    args=parser.parse_args();run(args.current,args.out)

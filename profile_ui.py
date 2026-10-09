"""Compare real GLES UI against the first build and 2.0.2.11, without user data."""
from pathlib import Path
import argparse, hashlib, json, subprocess, tarfile, tempfile, urllib.request

REPO='https://api.github.com/repos/Rukeru/nuvio-native-legacy-mdblist'
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Nuvio-public-UI-profile'}),timeout=180) as reply:
        return reply.read()
def run(current,out):
    current=Path(current).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    evidence={'hardware':'GitHub Linux runner / Mesa software GLES2; not a TV','baselines':[]}
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

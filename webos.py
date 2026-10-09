"""Independent webOS release channel in the same repository as Tizen.

webos-v tags never become GitHub's Latest release. The LG app filters the release
list; Samsung continues following releases/latest without any workflow changes.
"""
from pathlib import Path
import argparse, hashlib, io, json, os, re, shutil, struct, subprocess, tarfile
import urllib.request
from channel import api, UPSTREAM, CHANNEL, BASE, version
from resilience import fetch

SDK_URL = 'https://github.com/openlgtv/buildroot-nc4/releases/download/webos-a38c582/arm-webos-linux-gnueabi_sdk-buildroot-x86_64.tar.gz'
SDK_SHA = '04ad3311b48b4557a7002aef56ae2e167478e8e129f37daac04649bddf813616'

def package_version(tag, run):
    major, minor, patch = map(int, version(tag).split('.'))
    if not 0 < run < 100000 or patch >= 10000: raise ValueError('Version range needs maintenance')
    return f'{major}.{minor}.{patch*100000+run}'

def needed(upstream, releases, force=False):
    from update_guard import stable
    if upstream.get('draft') or upstream.get('prerelease'): return False
    published = stable(releases, 'webos-v')
    return force or published is None or ('<!-- webos-upstream-release: ' + str(upstream['id']) + ' -->') not in (published.get('body') or '')

def download(url, path, sha):
    if not re.fullmatch(r'[0-9a-f]{64}',sha): raise ValueError('Missing input SHA-256')
    req=urllib.request.Request(url,headers={'User-Agent':'Nuvio-MDBList-webOS'})
    path.write_bytes(fetch(req))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=sha: raise ValueError('Input checksum mismatch')

def ar_members(path):
    data=Path(path).read_bytes()
    if data[:8]!=b'!<arch>\n': raise ValueError('Not an IPK/ar package')
    pos=8
    while pos<len(data):
        h=data[pos:pos+60]
        if len(h)!=60 or h[58:]!=b'`\n': raise ValueError('Damaged IPK member')
        n=int(h[48:58]); name=h[:16].decode().strip().rstrip('/')
        if pos+60+n>len(data): raise ValueError('Truncated IPK')
        yield name,data[pos+60:pos+60+n]
        pos+=60+n+n%2

def inspect(path, expected_version):
    ar=dict(ar_members(path))
    if ar.get('debian-binary')!=b'2.0\n': raise ValueError('Unsupported IPK format')
    with tarfile.open(fileobj=io.BytesIO(ar['data.tar.gz'])) as t:
        files={m.name.lstrip('./'):m for m in t.getmembers() if m.isfile()}
        root='usr/palm/applications/space.nuvio.native.legacy/'
        info=json.load(t.extractfile(files[root+'appinfo.json']))
        if info['id']!='space.nuvio.native.legacy' or info['version']!=expected_version or info['type']!='native' or info['main']!='nuvio-proto': raise ValueError('Wrong LG package metadata')
        for n in files:
            if '..' in Path(n).parts or re.search(r'/(conta-|discord-p|jellyfin-p|emby-p|plex-p|mdblist-p[0-9]+\.txt)',n) or '/art/cache/' in n or '/art/collections/' in n or n.endswith('/mdblist.txt'): raise ValueError('Unexpected private file in package')
        for name in ['lib/dts-starfish-webos3.so','lib/dts-starfish-webos4.so','licenses/dts/COPYING.LGPLv2.1','licenses/dts/SOURCE.txt','licencas/p2p-avisos.txt']:
            if root+name not in files: raise ValueError('Missing native component: '+name)
        m=files[root+'nuvio-proto']
        if m.mode & 0o777 != 0o755: raise ValueError('Executable must be 755')
        b=t.extractfile(m).read()
        if b[:6]!=b'\x7fELF\x01\x01' or struct.unpack_from('<H',b,18)[0]!=40 or struct.unpack_from('<I',b,36)[0]&0x400: raise ValueError('Wrong ARM ABI')
        for marker in [b'nuvio-mdblist-webos/1',b'mdblist_scrobble',b'Nuvio Engine/',b'/releases?per_page=100']:
            if marker not in b: raise ValueError('Missing feature marker: '+repr(marker))
        versions={x.decode() for x in re.findall(rb'GLIBC_[0-9]+\.[0-9]+(?:\.[0-9]+)?',b)}
        glibc=max(versions,key=lambda x:tuple(map(int,x[6:].split('.'))))
        if tuple(map(int,glibc[6:].split('.')))>(2,12): raise ValueError('Raised firmware glibc requirement: '+glibc)
        return {'appinfo':info,'glibc_max':glibc,'binary_sha256':hashlib.sha256(b).hexdigest(),'binary_bytes':len(b),'mdblist_tracking_present':True,'dts_and_engine_preserved':True}

def discover(args):
    from update_guard import pages, stable, blocked
    upstream=stable(pages('repos/'+UPSTREAM+'/releases'))
    if upstream is None: raise ValueError('No stable official release')
    releases=pages('repos/'+CHANNEL+'/releases')
    do_build=needed(upstream,releases,args.force)
    v=package_version(upstream['tag_name'],args.run)
    state={'upstream':upstream,'upstream_version':version(upstream['tag_name']),
           'version':v,'core_version':v,'tag':'webos-v'+v,'build':do_build,'base_commit':BASE}
    if do_build and blocked('webos',state,args.force): do_build=state['build']=False
    Path('webos-state.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f: f.write('build='+str(do_build).lower()+'\n')
    print('webOS build required:',do_build,'| Upstream:',upstream['tag_name'])

def prepare(args):
    state=json.loads(Path('webos-state.json').read_text())
    root=Path('upstream').resolve()
    if 'integration' not in state or not root.is_dir(): raise ValueError('Run compatibility preflight first')
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if commit!=state['upstream_commit']:raise ValueError('Preflight checkout changed')
    app=root/'deploy/app/appinfo.json'; info=json.loads(app.read_text())
    if info['version']!=state['upstream_version']: raise ValueError('Release/source version mismatch')
    info['version']=state['version']; info['title']='Nuvio Legacy + MDBList'
    app.write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
    config=root/'tools/tizen-config.xml'
    config.write_text(config.read_text().replace('version="'+state['upstream_version']+'"','version="'+state['version']+'"'),encoding='utf8')
    props=Path(os.environ['NUVIO_PROPERTIES']).read_text()
    for k in ['NUVIO_SUPABASE_URL','NUVIO_SUPABASE_ANON_KEY','TV_LOGIN_WEB_BASE_URL']:
        if not re.search(r'^'+k+r'=\S+',props,re.M): raise ValueError('Missing shared app setting: '+k)
    recipe=root/'tools/p2p-motor/build-arm.sh'
    body=recipe.read_text(); short=re.search(r'^COMMIT=([0-9a-f]+)$',body,re.M).group(1)
    state['engine_commit']=api('repos/NuvioMedia/nuvio-engine/commits/'+short)['sha']
    body=body.replace('COMMIT='+short,'COMMIT='+state['engine_commit']).replace('--platform linux/arm64','--platform "${NUVIO_BUILD_PLATFORM:-linux/arm64}"')
    recipe.write_text(body,encoding='utf8')
    # Checksum-verified SDK is copied into the normal upstream Docker recipe.
    download(SDK_URL,root/'tools/webos-sdk.tar.gz',SDK_SHA)
    docker=root/'tools/Dockerfile'; body=docker.read_text()
    body=body.replace('RUN curl -fsSL "$SDK_URL" -o /tmp/sdk.tar.gz \\\n  && mkdir -p /opt \\', 'COPY webos-sdk.tar.gz /tmp/sdk.tar.gz\nRUN mkdir -p /opt \\')
    if 'COPY webos-sdk.tar.gz' not in body: raise ValueError('Upstream Docker SDK recipe needs review')
    docker.write_text(body,encoding='utf8')
    state['sdk_url']=SDK_URL; state['sdk_sha256']=SDK_SHA
    Path('webos-state.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    print('Prepared webOS',state['version'],'at exact upstream commit',state['upstream_commit'])

def package(args):
    state=json.loads(Path('webos-state.json').read_text()); root=Path('upstream'); dest=Path('release-webos'); dest.mkdir(exist_ok=True)
    packages=list(root.glob('*.ipk'))
    if len(packages)!=1: raise ValueError('Expected one standard LG package')
    validation=inspect(packages[0],state['version'])
    name='space.nuvio.native.legacy_'+state['version']+'_mdblist_arm.ipk'
    shutil.copy2(packages[0],dest/name)
    tracked=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).split(b'\0')
    with tarfile.open(dest/('source-webos-'+state['version']+'.tar.gz'),'w:gz') as t:
        for raw in tracked:
            if not raw: continue
            p=raw.decode()
            if p=='local.properties': raise ValueError('Private build properties tracked')
            t.add(root/p,arcname='nuvio-webos-'+state['version']+'/'+p,recursive=False)
    (dest/'SOURCE.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    (dest/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf8')
    shutil.copy2(root/'LICENSE',dest/'LICENSE')
    (dest/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(dest.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'),encoding='utf8')
    print('PASS: webOS package, metadata, MDBList, engine, DTS, private-file and firmware ABI checks.')

if __name__=='__main__':
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('discover'); d.add_argument('--run',type=int,required=True); d.add_argument('--force',action='store_true')
    sub.add_parser('prepare'); sub.add_parser('package')
    a=p.parse_args(); globals()[a.command](a)

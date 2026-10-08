"""Release polling, deterministic preparation and checked release artifacts.

No publishing credentials are used by the source build. Publishing is a separate job.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from shell_id import shell_id

UPSTREAM = 'iqui27/nuvio-native-legacy'
CHANNEL = 'Rukeru/nuvio-native-legacy-mdblist'
BASE = '0fcfa601650aba3d61fbb9f8f9d97738e2c75a4c'

def api(path, missing=False):
    req = urllib.request.Request('https://api.github.com/' + path,
        headers={'User-Agent': 'Nuvio-MDBList-channel', 'Accept': 'application/vnd.github+json'})
    token = os.environ.get('GH_TOKEN')
    if token: req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        if missing and e.code == 404: return None
        raise

def version(tag):
    if not re.fullmatch(r'v?\d+\.\d+\.\d+', tag):
        raise ValueError('Unsupported upstream version; review required: ' + tag)
    return tag.removeprefix('v')

def needed(upstream, published, force=False):
    if upstream.get('draft') or upstream.get('prerelease'): return False
    marker = '<!-- upstream-release: ' + str(upstream['id']) + ' -->'
    return force or published is None or marker not in (published.get('body') or '')

def discover(args):
    upstream = api('repos/' + UPSTREAM + '/releases/latest')
    published = api('repos/' + CHANNEL + '/releases/latest', missing=True)
    do_build = needed(upstream, published, args.force)
    v = version(upstream['tag_name'])
    core = v + '.' + str(args.run)
    info = {'upstream': upstream, 'version': v, 'core_version': core,
            'tag': 'v' + core, 'build': do_build, 'base_commit': BASE}
    Path(args.state).write_text(json.dumps(info, indent=2) + '\n')
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a') as f:
            f.write('build=' + str(do_build).lower() + '\n')
            f.write('tag=' + info['tag'] + '\n')
    print('Build required:', do_build, '| Upstream:', upstream['tag_name'])

def download(url, dest, digest=None):
    # All executable inputs come from the official release or official engine source.
    allowed = ('https://github.com/' + UPSTREAM + '/releases/download/',
               'https://raw.githubusercontent.com/NuvioMedia/nuvio-engine/')
    if not url.startswith(allowed): raise ValueError('Unexpected input URL')
    req = urllib.request.Request(url, headers={'User-Agent': 'Nuvio-MDBList-channel'})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, 'wb') as f:
        shutil.copyfileobj(r, f)
    if digest and 'sha256:' + hashlib.sha256(Path(dest).read_bytes()).hexdigest() != digest:
        raise ValueError('Official release download checksum mismatch')

def dependencies(args):
    # Upstream uses BSD tar's automatic stdin decompression. GNU tar needs -J.
    # Prepare the same xz sources before tpk.sh so its existing-directory check
    # skips that platform-specific extraction. Do not modify the packaging recipe.
    recipe = (Path(args.source) / 'tools/tpk.sh').read_text()
    cache = Path(args.cache) / 'src'
    cache.mkdir(parents=True, exist_ok=True)
    urls = re.findall(r'https://[^\s"\\]+\.tar\.xz', recipe)
    if not urls: raise ValueError('No upstream xz dependency URLs found; review recipe')
    for url in urls:
        name = url.rsplit('/', 1)[1].removesuffix('.tar.xz')
        folder = cache / name
        if folder.is_dir(): continue
        archive = cache / (name + '.tar.xz')
        req = urllib.request.Request(url, headers={'User-Agent': 'Nuvio-MDBList-channel'})
        try:
            with urllib.request.urlopen(req, timeout=120) as r, archive.open('wb') as f:
                shutil.copyfileobj(r, f)
            with tarfile.open(archive, 'r:xz') as t:
                if any(Path(m.name).parts[0] != name for m in t.getmembers()):
                    raise ValueError('Unexpected dependency archive root: ' + name)
                t.extractall(cache, filter='data')
            if not folder.is_dir(): raise ValueError('Missing extracted dependency: ' + name)
            print('Prepared upstream dependency:', name)
        except Exception:
            if folder.exists(): shutil.rmtree(folder)
            raise
        finally:
            archive.unlink(missing_ok=True)

def prepare(args):
    state = json.loads(Path(args.state).read_text())
    root = Path(args.source).resolve()
    subprocess.run(['git', 'clone', '--filter=blob:none', '--no-checkout',
        'https://github.com/' + UPSTREAM + '.git', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'fetch', 'origin', BASE], check=True)
    subprocess.run(['git', '-C', str(root), 'checkout', '--detach', state['upstream']['tag_name']], check=True)
    state['upstream_commit'] = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.run(['git', '-C', str(root), 'apply', '--3way', '--index', str(Path(args.patch).resolve())], check=True)
    actual = json.loads((root / 'deploy/app/appinfo.json').read_text())['version']
    if actual != state['version']: raise ValueError('Release tag and source version differ')
    props = Path(os.environ['NUVIO_PROPERTIES']).read_text()
    for name in ['NUVIO_SUPABASE_URL', 'NUVIO_SUPABASE_ANON_KEY', 'TV_LOGIN_WEB_BASE_URL']:
        if not re.search(r'^' + name + r'=\S+', props, re.M):
            raise ValueError('Build properties missing required setting: ' + name)
    engine_root = Path(args.engine).resolve() / 'tpk'
    inc = engine_root / 'include/nuvio_engine'
    inc.mkdir(parents=True, exist_ok=True)
    assets = state['upstream']['assets']
    asset = next(a for a in assets if a['name'] == 'Nuvio-' + state['version'] + '-NuvioTpk.tpk')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', asset.get('digest') or ''):
        raise ValueError('Official TPK lacks SHA-256; refusing unverified engine')
    temp = engine_root / 'official.tpk'
    download(asset['browser_download_url'], temp, asset['digest'])
    with zipfile.ZipFile(temp) as z:
        if z.testzip(): raise ValueError('Damaged official TPK')
        (engine_root / 'libnuvio_engine.so').write_bytes(z.read('lib/libnuvio_engine.so'))
    temp.unlink()
    recipe = (root / 'tools/p2p-motor/build-tpk.sh').read_text()
    commit = re.search(r'^COMMIT=([0-9a-f]{7,40})$', recipe, re.M).group(1)
    # Expand the engine ref to a full immutable commit.
    commit = api('repos/NuvioMedia/nuvio-engine/commits/' + commit)['sha']
    download('https://raw.githubusercontent.com/NuvioMedia/nuvio-engine/' + commit +
             '/include/nuvio_engine/nuvio_engine.h', inc / 'nuvio_engine.h')
    (inc / 'export.h').write_text('#pragma once\n#define NUVIO_ENGINE_API __attribute__((visibility("default")))\n')
    state['engine_commit'] = commit
    state['shell_id'] = shell_id(root, engine_root / 'libnuvio_engine.so')
    (root / 'build').mkdir(exist_ok=True)
    (root / 'build/mdblist-shell.sha256').write_text(state['shell_id'] + '\n')
    header = root / 'src/mdblistchannel.h'
    text = header.read_text()
    if text.count('"unconfigured"') != 1: raise ValueError('Unexpected channel header')
    header.write_text(text.replace('"unconfigured"', '"' + state['shell_id'] + '"'))
    Path(args.state).write_text(json.dumps(state, indent=2) + '\n')
    print('Prepared exact upstream commit:', state['upstream_commit'])
    print('Host/resource identity:', state['shell_id'])

def package(args):
    state = json.loads(Path(args.state).read_text())
    root = Path(args.source)
    dest = Path(args.output); dest.mkdir(parents=True, exist_ok=True)
    core = root / 'build/tpk/libnuvio.so'
    native = core.read_bytes()
    shell = state['shell_id']; v = state['core_version']
    packages = list((root / 'build/tpk').glob('*-NuvioTpk.tpk'))
    if len(packages) != 1: raise ValueError('Expected exactly one Tizen 8 package')
    target = dest / ('Nuvio-' + v + '-MDBList-Tizen8-unsigned.tpk')
    with zipfile.ZipFile(packages[0]) as z:
        if z.testzip(): raise ValueError('Damaged built package')
        names = z.namelist()
        manifest = ET.fromstring(z.read('tizen-manifest.xml'))
        ns = {'t': 'http://tizen.org/ns/packages'}
        if (manifest.get('version') != state['version'] or manifest.get('api-version') != '8' or
            manifest.find('t:profile', ns).get('name') != 'tv'):
            raise ValueError('Unexpected Tizen package target')
        if z.read('lib/libnuvio.so') != native: raise ValueError('Native package mismatch')
        if z.read('res/versao.txt').decode().strip() != v: raise ValueError('Packaged core version mismatch')
        if z.read('res/mdblist-shell.sha256').decode().strip() != shell: raise ValueError('Packaged shell identity mismatch')
        if any(re.search(r'(^|/)(conta-|discord-p|jellyfin-p|emby-p|plex-p)', n) or
               n.startswith(('res/art/cache/', 'res/art/collections/')) for n in names):
            raise ValueError('Private application data in package')
        for item in ['bin/NuvioTpk.dll', 'lib/libnuvio_engine.so', 'res/art/marcas/abertura.jpg',
                     'res/fonts/', 'res/licencas/p2p-avisos.txt']:
            if not any(n.startswith(item) for n in names): raise ValueError('Missing package content: ' + item)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as out:
            for n in names:
                if not re.fullmatch(r'(author-signature|signature\d+)\.xml', n): out.writestr(n, z.read(n))
    name = 'libnuvio-' + v + '-' + shell + '-mdblist-tpk-arm.so'
    (dest / name).write_bytes(native)
    # git's tracked files include all patched additions, exclude build properties/caches.
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).split(b'\0')
    with tarfile.open(dest / ('source-' + v + '.tar.gz'), 'w:gz') as archive:
        for raw in tracked:
            if not raw: continue
            p = raw.decode()
            if p == 'local.properties': raise ValueError('Build properties must never be tracked')
            archive.add(root / p, arcname='nuvio-' + v + '/' + p, recursive=False)
    (dest / 'SOURCE.json').write_text(json.dumps(state, indent=2) + '\n')
    shutil.copy2(root / 'LICENSE', dest / 'LICENSE')
    sums = ['%s  %s' % (hashlib.sha256(p.read_bytes()).hexdigest(), p.name)
            for p in sorted(dest.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.txt']
    (dest / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
    print('Validated unsigned Tizen package and native update:', target.name)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='command', required=True)
    d = sub.add_parser('discover'); d.add_argument('--run', type=int, required=True); d.add_argument('--force', action='store_true'); d.add_argument('--state', default='state.json')
    r = sub.add_parser('prepare'); r.add_argument('--source', default='upstream'); r.add_argument('--engine', default='engine'); r.add_argument('--patch', default='mdblist.patch'); r.add_argument('--state', default='state.json')
    c = sub.add_parser('dependencies'); c.add_argument('--source', default='upstream'); c.add_argument('--cache', required=True)
    b = sub.add_parser('package'); b.add_argument('--source', default='upstream'); b.add_argument('--state', default='state.json'); b.add_argument('--output', default='release')
    args = p.parse_args(); globals()[args.command](args)

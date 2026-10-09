"""Owned modules + independently diagnosed three-way upstream adapters.

Historical release patches remain immutable. Only this registry is used for 2.0.3+.
Never resolve a source conflict automatically or overwrite an upstream-owned module.
"""
from pathlib import Path
import ast
import argparse, hashlib, json, os, re, subprocess, sys
from resilience import retry

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / 'integration/manifest.json'

class Incompatible(RuntimeError): pass

def unpack():
    """The public source bundle is a transport archive, not an executable input."""
    if REGISTRY.exists():return
    import zipfile
    archive=ROOT/'integration-bundle.zip'
    digest=(ROOT/'integration-bundle.sha256').read_text().strip()
    verified(archive,digest)
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            # orig_filename retains backslashes before Windows ZipInfo normalizes them.
            name=entry.orig_filename
            p=Path(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
                raise Incompatible('Unsafe integration archive path')
        z.extractall(ROOT/'integration')

def manifest():
    unpack()
    return json.loads(REGISTRY.read_text(encoding='utf8'))

def fingerprint():
    # Includes updater/preflight code: a repaired adapter/check immediately unblocks.
    unpack()
    h=hashlib.sha256(REGISTRY.read_bytes())
    for path in ('integration.py','update_guard.py','resilience.py','channel.py','webos.py','preflight.sh','platform-checks.sh', 'tizen-build.sh','tizen_sdk.py','webos-build.sh','profile_ui.py','release_http.py','publish.py','publish_webos.py','.github/workflows/update.yml','.github/workflows/webos.yml'):
        p=ROOT/path
        if p.exists(): h.update(path.encode()+p.read_bytes())
    return h.hexdigest()

def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.STDOUT,text=True)

def report(platform, state, component, status, details='', files=()):
    value={'platform':platform,'upstream_tag':state['upstream']['tag_name'],
           'upstream_commit':state.get('upstream_commit'), 'integration':fingerprint(),
           'component':component,'status':status,'files':list(files),'details':details[-14000:],
           'run_url':os.environ.get('GITHUB_SERVER_URL','https://github.com')+'/'+os.environ.get('GITHUB_REPOSITORY','Rukeru/nuvio-native-legacy-mdblist')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','local')}
    folder=ROOT/'diagnostics';folder.mkdir(exist_ok=True)
    (folder/(platform+'-compatibility.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf8') as f:
            f.write(f'### {platform}: {status} — {component}\n\nUpstream `{value["upstream_tag"]}`; adapter `{value["integration"][:12]}`.\n\n')
            if files:f.write('Affected files: '+', '.join('`'+p+'`' for p in files)+'\n\n')
            if details:f.write('```text\n'+details[-8000:].replace('```','~~~')+'\n```\n\n')
    return value

def verified(path, digest):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise Incompatible('Integration input checksum mismatch: '+path.name)

def apply(root, platform, state):
    m=manifest()
    for entry in m['overlay']:
        path=root/entry['path']; owned=ROOT/'integration/overlay'/entry['path']
        verified(owned,entry['sha256'])
        if path.exists():
            report(platform,state,'owned-modules','source-conflict','Upstream now owns a custom module; reconcile it explicitly.',[entry['path']])
            raise Incompatible('Owned module collision: '+entry['path'])
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(owned.read_bytes())
        path.chmod(0o755 if entry['mode']=='100755' else 0o644)
    git(root,'add','--',*[e['path'] for e in m['overlay']])
    applied=[]
    translations(root,platform,state,m)
    for component in m['components']:
        if platform not in component['platforms']:continue
        patch=ROOT/'integration'/component['patch'];verified(patch,component['sha256'])
        try: git(root,'apply','--3way','--index',str(patch))
        except subprocess.CalledProcessError as error:
            conflicts=git(root,'diff','--name-only','--diff-filter=U').splitlines()
            report(platform,state,component['name'],'source-conflict',error.output,conflicts or component['files'])
            raise Incompatible('Adapt '+component['name']+' for '+state['upstream']['tag_name']) from error
        applied.append({'component':component['name'],'sha256':component['sha256']})
    state['integration']={'fingerprint':fingerprint(),'base_commit':m['base_commit'],'components':applied,'overlay':m['overlay']}
    from tizen_improvements import changelog
    changelog(root,state)
    contracts(root,platform,state)

def translations(root,platform,state,m):
    """Merge owned labels by decoded key, independent of line numbers/table offsets."""
    spec=m.get('translations')
    if not spec:return
    path=ROOT/'integration'/spec['file'];verified(path,spec['sha256'])
    entries=json.loads(path.read_text(encoding='utf8'))['entries']
    pattern=re.compile(r'(?:T\(|\{)\s*("(?:[^"\\]|\\.)*")\s*,\s*("(?:[^"\\]|\\.)*")')
    modified=[]
    for p in sorted(root.glob('src/idioma_*.h')):
        text=p.read_text(encoding='utf8');lines=text.splitlines();rows={};first=None;last=None
        for i,line in enumerate(lines):
            match=pattern.search(line)
            if not match:continue
            key=ast.literal_eval(match.group(1))
            if key in rows:raise Incompatible('Duplicate upstream language key: '+key)
            rows[key]=(line,match.group(2));first=i if first is None else first;last=i
        if first is None:raise Incompatible('Upstream translation format changed: '+p.name)
        locale=p.stem.removeprefix('idioma_');master=locale=='tab'
        for entry in entries:
            key=ast.literal_eval(entry['key'])
            target=entry.get('locales',{}).get(locale,{'value':entry['english'],'previous':None})
            desired=entry['english'] if master else target['value']
            previous=entry['previous'] if master else target['previous']
            if key in rows:
                line,value=rows[key]
                if previous is None and not master:continue # upstream supplied a new native translation
                if value not in (desired,previous):
                    report(platform,state,'translations','source-conflict','Upstream changed an owned translation key: '+key,[str(p.relative_to(root))])
                    raise Incompatible('Translation key changed: '+key)
                match=pattern.search(line);line=line[:match.start(2)]+desired+line[match.end(2):]
            else:line=('  { '+entry['key']+', '+desired+' },' if master else '  T('+entry['key']+', '+desired+'),')
            rows[key]=(line,desired)
        ordered=sorted(rows,key=lambda key:key.encode('utf8'))
        p.write_text('\n'.join(lines[:first]+[rows[key][0] for key in ordered]+lines[last+1:])+'\n',encoding='utf8',newline='\n')
        modified.append(str(p.relative_to(root)))
    git(root,'add','--',*modified)
    state['translation_overlay']=spec

def contracts(root,platform,state):
    requirements={
      'settings':{'src/ajustes.c':['#include "mdbsettings.def"','mdblist_rastrear','ajustes_season_numbers'],
                  'src/mdbsettings.def':['"mdblistScrobbleLocal", 1','"cachedOnlyDefaultLocal", 0','"showSeasonNumbersLocal", 0'],
                  'src/ajustes_ux_tela.inc':['#include "mdbsettings_tracking.inc"']},
      'account-history':{'src/contalib.c':['contalib_vistos_tick','vistoep_fonte(v->id'],
                         'src/vistoep.c':['pthread_mutex_lock(&mapLock)','lapBarra','vistoep_revisao'],
                         'src/sync.c':['mdb_credentials'],
                         'src/app.c':['contapend_lapides_guardadas(vistonao_guardada)'],
                         'src/contapend.c':['lapideGuardada(usuario, ents[i].perfil'],
                         'src/vistonao.h':['vistonao_guardada']},
      'playback-tracking':{'src/player.c':['mdblist','mdblist_scrobble'], 'src/mdblistlibrary.c':['/sync/watched']},
      'ui-performance-library':{'src/episodeindex.c':['episodeindex'], 'src/chartcache.c':['chartcache']},
      'app-updater-changelog':{'src/app.c':['mdbchangelog','contalib_vistos_tick']}}
    # This is a diagnostic contract, not proof of behavior: C fixtures + full build still gate publishing.
    for name,files in requirements.items():
        for file,tokens in files.items():
            text=(root/file).read_text(encoding='utf8')
            for token in tokens:
                if token not in text:
                    report(platform,state,name,'contract-failure','Required integration interface absent: '+token,[file])
                    raise Incompatible('Interface changed: '+name+' / '+file+' / '+token)
    for p in root.joinpath('src').glob('*'):
        if p.suffix in ('.c','.h','.inc','.def') and re.search(rb'^<<<<<<< |^=======\s*$|^>>>>>>> ',p.read_bytes(),re.M):
            raise Incompatible('Unresolved conflict markers: '+str(p))
    # A Settings option can exist while its category/preview index is displaced.
    visual=(root/'src/ajustes_ux_visual.inc').read_text(encoding='utf8')
    enum=re.search(r'enum \{\s*(AJS_REPRODUCAO.*?)AJS_N,',visual,re.S)
    arts=re.search(r'AJ_ARTE_SEC\[AJS_N \+ 1\]\[AJ_ARTE_BLOCOS\] = \{(.*?)\n\};',visual,re.S)
    catalog=(root/'src/ajustes_ux_tela.inc').read_text(encoding='utf8').replace('#include "mdbsettings_tracking.inc"',(root/'src/mdbsettings_tracking.inc').read_text(encoding='utf8'))
    sections=re.findall(r'\bSEC\(\s*"([^"]+)"',catalog)
    ids=re.findall(r'\bAJS_[A-Z_]+\b',enum.group(1)) if enum else []
    if not enum or not arts or len(ids)!=len(sections) or ids.count('AJS_TRACKING')!=1 or sections.count('Tracking')!=1 or ids.index('AJS_TRACKING')!=sections.index('Tracking') or len(re.findall(r'^\s*\{',arts.group(1),re.M))!=len(sections)+1:
        report(platform,state,'settings-presentation','contract-failure','Settings categories, Tracking placement and preview rows must stay aligned.',['src/ajustes_ux_visual.inc','src/ajustes_ux_tela.inc'])
        raise Incompatible('Settings presentation index changed')
    for name, command in [('settings-coverage',[sys.executable,str(root/'tests/ajustes_secoes.py'),str(root/'src/ajustes.c')]),
                          ('translation-coverage',[sys.executable,str(root/'tools/idiomas.py')])]:
        result=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        print(result.stdout,flush=True)
        if result.returncode:
            report(platform,state,name,'contract-failure',result.stdout)
            raise Incompatible('Compatibility coverage failed: '+name)
    report(platform,state,'all-adapters','source-compatible','Owned modules and component adapters passed. Syntax and behavior checks follow before the SDK build.')

def prepare(platform,state_file,source='upstream'):
    state=json.loads(Path(state_file).read_text(encoding='utf8'));root=Path(source).resolve()
    base=manifest()['base_commit']
    if root.exists():raise Incompatible('Source checkout already exists; use a fresh runner.')
    # Retry network fetching, not git apply/compilation. Clone is a local init + bounded fetch,
    # so a interrupted fetch can be safely repeated in the same fresh directory.
    root.mkdir();subprocess.run(['git','init',str(root)],check=True)
    git(root,'remote','add','origin','https://github.com/iqui27/nuvio-native-legacy.git')
    def fetch(ref):
        from update_guard import network_command
        network_command(['git','-C',str(root),'fetch','--no-tags','origin',ref])
    fetch(base)
    tag=state['upstream']['tag_name']
    if not re.fullmatch(r'v?\d+\.\d+\.\d+',tag):raise Incompatible('Unsupported official tag')
    fetch('refs/tags/'+tag)
    git(root,'checkout','--detach','FETCH_HEAD')
    state['upstream_commit']=git(root,'rev-parse','HEAD').strip()
    Path(state_file).write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    apply(root,platform,state)
    Path(state_file).write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
    print('Prepared compatible source:',state['upstream_commit'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--platform',choices=['tizen','webos'],required=True);p.add_argument('--state',required=True);p.add_argument('--source',default='upstream')
    a=p.parse_args()
    try:prepare(a.platform,a.state,a.source)
    except Exception as error:
        path=ROOT/'diagnostics'/f'{a.platform}-compatibility.json'
        if not path.exists() and Path(a.state).exists():
            from resilience import transient
            report(a.platform,json.loads(Path(a.state).read_text()),'source-preparation',
                   'transient-failure' if transient(error) or (isinstance(error,subprocess.CalledProcessError) and __import__('update_guard').network_log(error.output or '')) else 'contract-failure',str(error))
        print('Compatibility preflight failed:',error,file=sys.stderr);raise

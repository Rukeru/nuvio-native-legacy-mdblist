"""Apply reviewed shared TV improvements after the common MDBList patch."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess

PATCHES = ('tizen-01-source-cache.patch', 'tizen-02-season-charts.patch',
           'tizen-03-mdblist-watchlist.patch', 'tizen-04-mdblist-continue.patch',
           'tizen-05-mdblist-account-key.patch',
           'shared-06-tracking-performance-layout.patch',
           'shared-07-progress-home-performance.patch',
           'shared-08-watched-history-sync.patch',
           'shared-09-installed-changelog.patch',
           'shared-10-changelog-modal-guards.patch',
           'shared-11-changelog-readability.patch')

def changelog(source, state):
    """Embed bounded public release highlights, never fetch from the TV UI."""
    notes = [
        ("Your watched history", "Watched movies and episodes from Nuvio and MDBList now appear on your TV, including older watches."),
        ("A smoother TV experience", "The recent Home and season-progress performance improvements are included."),
        ("What changed, at a glance", "A short changelog appears after updates. Reopen it any time from Settings > About & help > What's new."),
    ]
    upstream = state.get('upstream', {})
    version = re.sub(r'[^A-Za-z0-9. -]', '', upstream.get('tag_name', 'official release'))[:40]
    notes.append(("Official Nuvio features", "Includes the features and fixes from Nuvio " + version.removeprefix('v') + "."))
    body = re.sub(r'<!--.*?-->|```.*?```', '', upstream.get('body') or '', flags=re.S)
    for raw in body.splitlines():
        if len(notes) >= 6: break
        if not re.match(r'^\s*[-*+]\s+', raw): continue
        text = re.sub(r'^\s*[-*+]\s+', '', raw)
        text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)
        text = re.sub(r'<[^>]*>|https?://\S+', '', text)
        text = re.sub(r'[*_`#]|[\x00-\x1f\x7f]', '', text)
        text = ' '.join(text.split())
        if not text or re.search(r'\b(install|download|donat|sdk|gcc|cmake|secret|token|key|sha256|curl|sudo|\.tpk|\.ipk)\b', text, re.I): continue
        if len(text) > 170:
            text = text[:167].rsplit(' ', 1)[0] + '…'
        notes.append(("From the official release", text))
    literal = lambda s: json.dumps(s, ensure_ascii=False)
    header = '/* Generated from the reviewed custom changes and pinned public release. */\n'
    installed = state.get('core_version', state.get('version', 'preview'))
    if re.fullmatch(r'[0-9.]+', installed):
        header += '/* Installed-version preview: ' + installed + ' */\n'
    header += 'static const struct { const char *title, *body; } MDB_CHANGES[] = {\n'
    header += ''.join('  { ' + literal(title) + ', ' + literal(body) + ' },\n' for title, body in notes)
    header += '};\n'
    path = Path(source) / 'src/mdbchangelog_notes.h'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header, encoding='utf8', newline='\n')
    state['installed_changelog'] = {'upstream_tag': upstream.get('tag_name'), 'entries': len(notes),
                                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return notes

def apply(source, state_file):
    root = Path(__file__).resolve().parent
    provenance = []
    for name in PATCHES:
        patch = root / name
        subprocess.run(['git', '-C', str(source), 'apply', '--3way', '--index',
                        str(patch)], check=True)
        provenance.append({'patch': name, 'sha256': hashlib.sha256(patch.read_bytes()).hexdigest()})
    state = json.loads(Path(state_file).read_text())
    state['tizen_improvements'] = provenance
    changelog(source, state)
    Path(state_file).write_text(json.dumps(state, indent=2) + '\n')
    print('Applied shared TV improvements and fixes; source provenance recorded')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='upstream')
    parser.add_argument('--state', default='state.json')
    args = parser.parse_args()
    apply(args.source, args.state)

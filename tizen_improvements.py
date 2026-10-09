"""Apply reviewed shared TV improvements after the common MDBList patch."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PATCHES = ('tizen-01-source-cache.patch', 'tizen-02-season-charts.patch',
           'tizen-03-mdblist-watchlist.patch', 'tizen-04-mdblist-continue.patch',
           'tizen-05-mdblist-account-key.patch',
           'shared-06-tracking-performance-layout.patch',
           'shared-07-progress-home-performance.patch')

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
    Path(state_file).write_text(json.dumps(state, indent=2) + '\n')
    print('Applied shared TV improvements and fixes; source provenance recorded')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='upstream')
    parser.add_argument('--state', default='state.json')
    args = parser.parse_args()
    apply(args.source, args.state)

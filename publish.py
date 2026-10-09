"""Publish a complete, validated release. The build job has no write token."""
from pathlib import Path
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

repo = os.environ['GITHUB_REPOSITORY']
if repo != 'Rukeru/nuvio-native-legacy-mdblist': raise SystemExit('Wrong update repository')
token = os.environ['GH_TOKEN']
dest = Path('release')
state = json.loads((dest / 'SOURCE.json').read_text())
expected = {}
for line in (dest / 'SHA256SUMS.txt').read_text().splitlines():
    sha, name = line.split('  ', 1)
    if Path(name).name != name: raise SystemExit('Invalid artifact path')
    if hashlib.sha256((dest / name).read_bytes()).hexdigest() != sha:
        raise SystemExit('Artifact checksum mismatch: ' + name)
    expected[name] = 'sha256:' + sha
expected['SHA256SUMS.txt'] = 'sha256:' + hashlib.sha256((dest / 'SHA256SUMS.txt').read_bytes()).hexdigest()

from release_http import request, delete_asset
base = 'https://api.github.com/repos/' + repo
body = ('MDBList-preserving Tizen 8 build of upstream ' + state['upstream']['tag_name'] + '.\n\n'
        'Compatible native updates download on the home screen and apply on the next full app launch. '
        'Changed host/resources/engine require installation of the new unsigned TPK with TV signing.\n\n'
        'SHA-256 and MDBList/shell compatibility checks passed before publication. '
        'Physical-TV playback is not tested by this build.\n\n'
        'Upstream release: ' + state['upstream']['html_url'] + '\n'
        'Upstream commit: ' + state['upstream_commit'] + '\n'
        'Host/resource identity: `' + state['shell_id'] + '`\n\n'
        '<!-- upstream-release: ' + str(state['upstream']['id']) + ' -->\n')
# Failed publication leaves a draft; reruns can replace that draft, never a live release.
releases = request(base + '/releases?per_page=100')
existing = next((r for r in releases if r['tag_name'] == state['tag']), None)
if existing and not existing['draft']: raise SystemExit('Release already published')
if existing:
    release = existing
    for asset in release['assets']:
        delete_asset(asset['id'])
else:
    release = request(base + '/releases', {'tag_name': state['tag'],
        'target_commitish': os.environ['GITHUB_SHA'], 'name': 'Nuvio ' + state['core_version'] + ' + MDBList',
        'draft': True, 'prerelease': False, 'body': body})
upload = release['upload_url'].split('{')[0]
for name in sorted(expected):
    request(upload + '?name=' + urllib.parse.quote(name), (dest / name).read_bytes(), binary=True)
for attempt in range(6):
    current = request(base + '/releases/' + str(release['id']))
    actual = {a['name']: a.get('digest') for a in current['assets']}
    if actual == expected: break
    if attempt == 5: raise SystemExit('GitHub asset digests not verified; release remains draft')
    time.sleep(10)
request(base + '/releases/' + str(release['id']), {'draft': False, 'make_latest': 'true', 'body': body}, 'PATCH')
print('Published checked update release:', state['tag'])
from update_guard import recovered
recovered('tizen', state)

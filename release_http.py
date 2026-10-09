"""Retry idempotent release operations; reconcile ambiguous POST outcomes."""
import json, os, time, urllib.parse, urllib.request
from resilience import retry, transient
from update_guard import api, REPO

def request(url,data=None,method=None,binary=False):
    headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'Nuvio-MDBList-channel',
             'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    body=data
    if data is not None:
        headers['Content-Type']='application/octet-stream' if binary else 'application/json'
        body=data if binary else json.dumps(data).encode()
    req=urllib.request.Request(url,data=body,headers=headers,method=method)
    def once():
        with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
    if data is None or method=='PATCH':return retry(once)
    for attempt in range(3):
        try:return once()
        except Exception as error:
            if not transient(error):raise
            if binary:
                # Upload URL includes immutable release ID. A completed upload can
                # be found by name/digest. Delete an incomplete draft asset only.
                import hashlib,re
                release_id=re.search(r'/releases/(\d+)/assets',url).group(1)
                release=api(f'repos/{REPO}/releases/{release_id}')
                if not release['draft']:raise RuntimeError('Refusing to modify live release assets')
                name=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['name'][0]
                asset=next((a for a in release['assets'] if a['name']==name),None)
                if asset and asset.get('digest')=='sha256:'+hashlib.sha256(data).hexdigest():return asset
                if asset:delete_asset(asset['id'])
            else:
                # Lost create-release response: recover the exact tag's draft.
                if not url.endswith('/releases'):raise
                from update_guard import pages
                existing=next((r for r in pages(f'repos/{REPO}/releases') if r['tag_name']==data['tag_name']),None)
                if existing:
                    if not existing['draft']:raise RuntimeError('Tag already published')
                    return existing
            if attempt==2:raise
            time.sleep(5*2**attempt)

def delete_asset(asset_id):
    from urllib.error import HTTPError
    req=urllib.request.Request(f'https://api.github.com/repos/{REPO}/releases/assets/{asset_id}',method='DELETE',
        headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'Nuvio-MDBList-channel'})
    def once():
        try:
            with urllib.request.urlopen(req,timeout=60):return
        except HTTPError as error:
            if error.code!=404:raise
    retry(once)

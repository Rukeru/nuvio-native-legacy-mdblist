"""Prepare development-only packages after exact-commit development validation.

This entry point has no publishing, release-discovery writes or TV installation.
"""
from pathlib import Path
import argparse, json, os
from channel import api, CHANNEL, select_upstream


def prepare(platform, evidence_run):
    sha = os.environ['GITHUB_SHA']
    if os.environ['GITHUB_REF'] != 'refs/heads/codex/discover-profile-appearance':
        raise ValueError('Test packages are restricted to the existing development branch')
    run = api(f'repos/{CHANNEL}/actions/runs/{evidence_run}')
    if (run['head_sha'] != sha or run['head_branch'] != 'codex/discover-profile-appearance'
            or run['path'] != '.github/workflows/development.yml'
            or run['status'] != 'completed' or run['conclusion'] != 'success'):
        raise ValueError('Require successful development validation of this exact commit')
    upstream, selection = select_upstream(True)
    # Retain package versions for in-place replacement/rollback. These are the
    # published baseline versions, not a new production release or update asset.
    version = '2.0.4' if platform == 'tizen' else '2.0.400064'
    state = dict(upstream=upstream, upstream_version='2.0.4', version=version,
                 core_version='2.0.4.9001' if platform == 'tizen' else version,
                 builder_commit=sha, diagnostic_only=True, development_test_only=True,
                 development_evidence_run=evidence_run, **selection)
    path = 'state.json' if platform == 'tizen' else 'webos-state.json'
    Path(path).write_text(json.dumps(state, indent=2)+'\n', encoding='utf8')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('platform', choices=['tizen', 'webos'])
    parser.add_argument('evidence_run', type=int)
    args = parser.parse_args()
    print(prepare(args.platform, args.evidence_run))

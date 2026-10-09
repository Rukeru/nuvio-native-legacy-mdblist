#!/bin/bash
set -euo pipefail
python3 channel.py dependencies --cache "$NUVIO_TPK_CACHE"
python3 tizen_sdk.py
export NV_MDBLIST_VERSION="$(python3 -c 'import json;print(json.load(open("state.json"))["core_version"])')"
bash upstream/tools/env.sh --require-core >/dev/null
bash upstream/tools/tpk.sh

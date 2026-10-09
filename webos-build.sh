#!/bin/bash
set -euo pipefail
mkdir -p "$RUNNER_TEMP/webos-cache"
if [ -f "$RUNNER_TEMP/webos-cache/sdk-image.tar.zst" ]; then
  zstd -dc "$RUNNER_TEMP/webos-cache/sdk-image.tar.zst" | docker load
else
  docker build --platform linux/amd64 -t nuvio-webos-sdk upstream/tools
  docker save nuvio-webos-sdk | zstd -T0 -3 > "$RUNNER_TEMP/webos-cache/sdk-image.tar.zst"
fi
bash upstream/tools/p2p-motor/build-arm.sh "$NUVIO_P2P_MOTOR/arm"
export NUVIO_ARES_PACKAGE="$RUNNER_TEMP/lg-cli/node_modules/.bin/ares-package"
bash upstream/tools/env.sh --require-core >/dev/null
bash upstream/tools/arm.sh --ipk --build
python3 webos.py package

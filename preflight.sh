#!/bin/bash
# Run with minimal development headers, before TV SDK/engine/private build settings.
set -euo pipefail
component=compatibility-setup
trap 'echo "::integration-component::$component"' ERR
platform="$1"
if [ "$platform" = tizen ]; then
  component=tizen-sdk
  python3 tizen_sdk.py --check
fi
cd upstream
flags=(-std=gnu11 -UNDEBUG -Isrc)
read -ra sdl <<< "$(sdl2-config --cflags)"
if [ "$platform" = webos ]; then flags+=(-DNV_WEBOS); fi
for module in discover discover_catalog profilestats menu ajustes app catalogo contalib contapend visto vistoep vistonao sync perfis addons player streams descoberta vertudo mdblistlibrary mdblistscrobble nvdiag nvdiag_format avisos registro telemetria diagnostico trakt sessao main; do
  component="interface-$module"
  echo "Compatibility syntax: $module ($platform)"
  cc "${flags[@]}" "${sdl[@]}" -fsyntax-only "src/$module.c"
done
component=provider-discover-statistics-tests
bash tests/discover.sh
bash tests/profilestats.sh
component=settings-defaults-tests
bash tests/mdblist_settings_defaults.sh
component=shared-settings-history-performance-tests
bash tests/tizen_improvements.sh
component=mdblist-scrobbling-tests
bash tests/mdblist.sh
component=app-update-channel-tests
bash tests/mdblist_channel.sh
component=watched-history-unwatch-tests
bash tests/contapend.sh
bash tests/vistonao.sh
component=watched-history-concurrency-tests
bash tests/vistoep_corrida.sh
component=account-sync-tests
CPATH="$(sdl2-config --prefix)/include:${CPATH:-}" bash tests/syncaddons.sh

#!/bin/bash
# Run with minimal development headers, before TV SDK/engine/private build settings.
set -euo pipefail
platform="$1"
cd upstream
flags=(-std=gnu11 -UNDEBUG -Isrc)
read -ra sdl <<< "$(sdl2-config --cflags)"
if [ "$platform" = webos ]; then flags+=(-DNV_WEBOS); fi
for module in ajustes app catalogo contalib contapend visto vistoep sync player streams descoberta vertudo mdblistlibrary mdblistscrobble; do
  echo "Compatibility syntax: $module ($platform)"
  cc "${flags[@]}" "${sdl[@]}" -fsyntax-only "src/$module.c"
done
bash tests/tizen_improvements.sh
bash tests/mdblist.sh
bash tests/mdblist_channel.sh
bash tests/vistonao.sh
bash tests/vistoep_corrida.sh
CPATH="$(sdl2-config --prefix)/include:${CPATH:-}" bash tests/syncaddons.sh

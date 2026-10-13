#!/bin/bash
set -euo pipefail
platform="$1"
component=trakt-scrobbling-tests
trap 'echo "::integration-component::$component"' ERR
cc -std=c11 -Wall -Wextra -Werror -Iupstream/src upstream/tests/trakt_scrobble.c upstream/src/traktscrobble.c -lm -o "$RUNNER_TEMP/trakt-check"
"$RUNNER_TEMP/trakt-check"
if [ "$platform" = webos ]; then
  component=webos-update-channel-tests
  cc -std=c11 -Wall -Wextra -Werror -DNV_WEBOS -ffunction-sections -fdata-sections -Wl,--gc-sections -Iupstream/src upstream/tests/mdblist_webos.c upstream/src/mdblistwebos.c -o "$RUNNER_TEMP/webos-check"
  "$RUNNER_TEMP/webos-check"
  python3 -c 'import pathlib,sys; assert b"nuvio-mdblist-webos/1" in pathlib.Path(sys.argv[1]).read_bytes()' "$RUNNER_TEMP/webos-check"
else
  component=translation-runtime-tests
  cc -std=c11 -Wall -Wextra -Iupstream/src $(sdl2-config --cflags) upstream/tests/idioma.c upstream/src/idioma.c -o "$RUNNER_TEMP/language-check"
  "$RUNNER_TEMP/language-check"
fi

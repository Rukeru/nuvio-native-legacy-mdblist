# Nuvio Legacy with MDBList — Tizen 8 and webOS update channels

This companion repository rebuilds **published releases** of
[iqui27/nuvio-native-legacy](https://github.com/iqui27/nuvio-native-legacy),
reapplying MDBList playback tracking before publication. It is intended for
**Rukeru/nuvio-native-legacy-mdblist**. It is an independent custom build.

The update channel is configured. Its first cloud build and publication passed,
and a subsequent workflow confirmed that an unchanged upstream release is skipped.
Only shared settings from the official public app are stored in the encrypted
Actions build secret; personal login details and MDBList keys are excluded.

For 2.0.3 and later, see [automatic update safeguards](UPDATER.md): hourly
platform checks, named component adapters, compatibility tests before SDK setup,
bounded transport retries and automatic issues for incompatible upstream changes.

## LG webOS

LG packages and automatic updates are also available in this repository. Read
[the webOS instructions](WEBOS.md) for installation, Homebrew Channel requirements
and the separate LG release channel. Samsung continues using Latest unchanged.

## Install once

1. Download the unsigned Tizen 8 TPK from [the latest custom release](https://github.com/Rukeru/nuvio-native-legacy-mdblist/releases/latest).
2. Sign it for your TV and install it. The custom package installs the MDBList
   integration and its compatible update channel.
3. Add your MDBList API key under **Settings → Tracking → MDBList**, or let account sync import the API key saved in Nuvio Desktop.
4. Open **Settings → Account and profiles → Tracking → Track playback with
   MDBList** and enable it for each profile you want to track.

The repository, Actions schedule and `NUVIO_BUILD_PROPERTIES` secret are already
configured for Rukeru. Never commit the properties file or put a personal MDBList
key in that build secret. A new copy of this repository needs those settings
configured separately before its builds can preserve sign-in.

The app service properties preserve Nuvio sign-in, account sync and existing
service integrations. They identify the original app's backend, rather than your
personal login. An empty build is deliberately refused because it would break sign-in.
Supported property names are in upstream `tools/env.sh`: `NUVIO_SUPABASE_URL`,
`NUVIO_SUPABASE_ANON_KEY`, `TV_LOGIN_WEB_BASE_URL`, `TRAKT_CLIENT_ID`,
`TRAKT_CLIENT_SECRET`, `SIMKL_CLIENT_ID`, `SIMKL_APP_NAME`, `TMDB_API_KEY`,
`SEEKR_API_KEY`, `NUVIO_REC_URL`, and `DISCORD_CLIENT_ID`.

## What happens after activation

- GitHub checks for a new published upstream release every hour. Scheduled
  runs can be delayed by GitHub; this is not an immediate release webhook.
- It assembles verified owned modules and named three-way component adapters, runs tracking
  and update tests, builds with the upstream ARM Docker toolchain, checks the
  actual ELF and Tizen 8 package, and publishes only after verifying GitHub's
  uploaded asset SHA-256 digests. A conflict or failure leaves the current live
  release intact. A failed upload leaves an unpublished draft.
- The TV checks on the home screen and downloads a compatible native core in the
  background. It applies on the next **full process restart**. Resuming a suspended
  app can keep the previous core running; use the existing restart action when offered.
- No update forces a restart during playback. MDBList remains opt-in per profile.
- Releases use a fourth version component for custom rebuilds, for example
  `2.0.2.1`, while the Tizen package manifest retains the upstream three-part version.
- Only assets from this repository, with the exact MDBList/shell suffix and a
  GitHub SHA-256 digest, are selected. Before loading a staged core, the host checks
  its ARM format, checksum, newer version, exported MDBList contract and matching
  shell/resources/engine identity. A rejected staged core falls back to the bundled
  custom core. These are compatibility checks, not a sandbox for native code.

## When a reinstall or maintenance is needed

The updater changes the native playback core. It cannot replace installed .NET
host code, artwork, fonts or the separate playback engine. These inputs are hashed;
when they change upstream, the old TV app skips the incompatible core. Sign and
install that release's new TPK to resume automatic core updates. This intentionally
avoids guessing that a new core will work with an old shell.

An upstream change can conflict with the MDBList patch. Repair the patch and use
**Run workflow → force** to rebuild the current release. Failed Actions runs appear
in the repository and GitHub's configured failure notifications; no broken release
is promoted automatically.

GitHub may disable scheduled workflows after 60 days without repository activity.
Check that Actions remains enabled; the workflow also makes a small monthly
maintenance commit on successful scheduled runs to keep the repository active.
See [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Validation and source

Local checks cover fake-service MDBList tracking, Trakt regressions, translation
tables, trusted-channel selection, malformed ELF rejection, real upstream core
rejection, wrong checksums, shell mismatch and fork version ordering. The local
bootstrap Tizen 8 host/core compiled successfully. The GitHub Linux ARM build, Tizen 8 package validation and release publication
also passed. The downloaded package and real native core were checked independently.
Neither live MDBList credentials nor a physical TV were exercised here.

`SOURCE.json` and the corresponding patched source archive accompany each cloud
release. The official engine's release checksum and exact source commit are recorded.
Third-party source URLs and native build instructions remain in upstream tools.
This repository uses the upstream GPL-3.0 license; third-party notices are retained.

## Preserved shared TV improvements

Both channels preserve strict cached-source filtering, the season-chart
performance toggle, MDBList Watchlist and MDBList Continue Watching. Read
[Shared improvements and limitations](TIZEN-IMPROVEMENTS.md). The original
integration and eleven reviewed shared patches are applied and tested on every
Samsung and LG rebuild, followed by the platform-specific updater. Read
[DEVELOPMENT_LESSONS.md](DEVELOPMENT_LESSONS.md) for confirmed causes, safeguards
and verification limits.

The user confirmed working automatic MDBList API-key sync on 2.0.2.11. The native
account reader and credential persistence are preserved. Manual entry in Tracking
is an optional fallback. No personal key belongs in this repository or build secret.

Your Progress now uses indexed, consistent watched snapshots and a readable
season window, with production rendering limited to visible rows. A full-card texture experiment remains benchmark-only; fewer draws did not establish a speedup. Existing chart caches retain their graphics budget.
Home reads compact MDBList Up Next identifiers without copying API keys per card.
The Samsung workflow compares actual GLES UI against published 2.0.2.3 and
2.0.2.11 and retains `ui-profile-evidence`; host results do not prove TV FPS.


Watched-history imports now merge MDBList movies/episodes and Nuvio account
history alongside Trakt. Background reads are independent of Continue Watching
and playback-reporting consent; small indexed batches preserve the successful
performance renderer. TV unwatch intent is protected from older snapshots.
See DEVELOPMENT_LESSONS.md for verification, identity and history-size limits.


## Installed update changelog

After an update, a compact **What's new** card appears once when Home is ready.
It shows the installed version and short release highlights, with three cards
per page, with readable controls even when your accent colour is very pale. Use Left/Right to change pages and OK or Back to dismiss. Reopen it
from **Settings > About & help > What's new** at any time.

The notes are embedded in the native build, including bounded highlights from
the exact official release used by that build. A local dismissal marker survives
restarts and later updates. The card waits for login, profile selection, playback
and other overlays, including search and keyboards, to finish. It makes no network requests and performs no file
reads after the once-per-process check; closed Home rendering remains unchanged.

Both Samsung core updates and LG package updates include these shared changelog patches.
SOURCE.json records its digest and the generated notes digest. Remote controls,
pagination, relaunches, failed persistence and scaled layout are regression-tested.
The real GLES fixture captures the generated cards. The existing Home/progress
comparison may be reused only when the official source and all eight earlier
patch digests are identical; other source changes run the full comparison again.

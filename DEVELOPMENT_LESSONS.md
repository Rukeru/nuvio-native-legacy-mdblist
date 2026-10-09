# Development lessons

Consult this document before changing the integration or release patch chain.

## Evidence reviewed on 9 October 2026

Reviewed source commits 48fe4fd through c7f073e, the original common MDBList
patch, the 2.0.2.7 and 2.0.2.8 reports, and both current build workflows.
The user's first-build success and later failures are observations; no
authenticated account response is available to establish their account's state.

* The original tracker authenticates with `?apikey=`. The later library uses
  `Authorization: Bearer` with that same key. The current official schema
  distinguishes query API keys from OAuth access tokens. Use API-key
  authentication consistently and test the transport contract, not a mock that
  merely repeats the implementation's header assumptions.
* Native account sync previously omitted the official profile settings key
  and serialized provider credentials. Preserve patch 5's bounded parser and
  explicit-removal semantics. Missing cloud data cannot prove a key was removed.
* The Collections five-column grid can extend into its fixed details panel.
  Derive column count from usable width and reserve focus growth and a gutter;
  use the same count for rendering, scrolling, hit targets and navigation.
* Detail episode lookup scans all episodes for every column and count query.
  A season index invalidated by catalogue revision avoids repeated scans while
  preserving catalogue order. Existing rendering already culls offscreen cards.
* MDBList pause AND stop mark watched at >=80%. A client threshold above 80%
  needs a capped remote progress value until the chosen threshold is reached.
  Keep exact resume seconds locally; do not advertise exact cross-device progress
  in the capped interval. Never change Trakt's independent threshold rules.
* Credentials must be scoped to account and profile, masked in UI, excluded
  from exports/build artifacts, and cleared from active memory when scope changes.
* Previous cloud failure was a test pthread typedef collision with glibc.
  Retain distinct deterministic scheduler typedefs. Successful compilation is
  not physical-device verification.
* LG and Samsung release channels are separate. LG must never become Latest;
  preserve app IDs, LG version mapping and the Samsung host/core contract.

## Verification boundaries

Desktop 0.1.29-alpha was checked at commit
80d8ce33d802ca24e162464350b146fcbbdd12a9. Its API-key provider credential
and typed `features.mdblist_settings.mdblist_api_key` exports match patch 5.
OAuth browser connections are a different credential type; an API-key reader
cannot manufacture a personal API key from an OAuth login.

The current schema was fetched again with browser headers after a bare request
returned 403. `/user` supports API-key validation and returns username/user_id.
Keep HTTP failure classification when it propagates through a library parser;
a generic follow-up error must not overwrite an earlier 401 or 429.

Manual edits and disconnects persist as pending account writes. Older cloud
replies cannot overwrite them before acknowledgement. Writes capture account
and profile; unsupported server writes retain the local key and show status.
The credential file uses atomic replacement and owner-only permissions in the
existing app data directory. This is not an encrypted hardware keychain.

Regression fixtures passed for restart, missing/invalid cloud data, manual
overrides, pending removal, storage/write failures, scope switching, API-key
transport, authentication/rate-limit errors, 85%/95% thresholds and dedup.
The episode benchmark uses 72, 888 and 1200 synthetic entries: 1000 frames of
12 lookups in the last season fall from 654000/10446000/14190000 catalogue
reads to 72/888/1200 reads. The index uses 4824 bytes; these are host counts,
not measured Simpsons TV frame rates. Progress summary capacity now matches
the catalogue's 1200 entries rather than truncating after 1024.

Controlled fixtures can verify requests, lifecycle, isolation, thresholds,
layout geometry and catalogue costs. Live account acceptance, real TV frame
times, playback and installation remain pending until measured on hardware.
Do not infer a TV frame rate from host CPU timings or the attached 60 FPS photo.

Connection diagnostics must recover on a later successful authenticated read or
write. A transient error must not leave a permanent failed status. Local storage
status describes saved credentials; API validation has its own connection row.
The library fixture covers failure followed by a successful retry.

## User follow-up and performance investigation

The user confirmed that 2.0.2.11 automatically synchronized their MDBList key.
Preserve mdbcredentials.c and sync.c unchanged. Reviewing Desktop's local OAuth
store did not establish that this user's account lacked a separately exported
API key; do not insist on manual entry when native account sync has succeeded.

Your Progress is separate from Season by the Numbers; the chart toggle hides
the latter only. Its data cache already avoided stable-frame recomputation.
The rebuild did a linear map lookup per episode: 8,880,600 visits for 1200
episodes in an 8000-entry synthetic watched map. A bounded 32 KiB hash index
reduces this to 2,569 probes. Real network writes could reallocate that map
while UI readers traversed it; a mutex and consistent batch snapshot protect it.
Only watched changes to the visible series invalidate its cached totals.

Large season sets were squeezed into four columns, producing rows shorter
than their labels and progress-bar overflow. A readable focus-following window
keeps every season reachable. Preserve entry animations and draw only visible
rows. A full-card texture experiment reduced 37-season draws from 159 to 11,
but Mesa submission time rose from about 0.9 to 4.2 ms. Fewer draws alone do
not establish a speedup: measure completion too. Keep this texture experiment
behind a benchmark-only definition; production uses the visible direct path
and cached/indexed data. Release hidden/closed Numbers targets and retain the
existing 6 MiB budget. Test counts, revisions, navigation geometry, concurrent
growth, invalidation and GL screenshots, not just compilation.

Per-card Home checks copied keys and reformatted the same Up Next IDs. A compact
scoped snapshot eliminates that work and avoids the network/data lock on render.
It does not change mdbcredentials.c, sync.c or tracking endpoints. Compare real
GLES rendering with published first build 2.0.2.3 and 2.0.2.11. Host timings and
synthetic draws cannot establish restored 60 FPS on the user's Samsung TV.
The performance meter's tracking timings contain only durations and sample
counts, never credentials or content identifiers.

## Watched-history import follow-up

The user confirmed the shared-07 Samsung performance is now perfect on their
TV. Preserve its renderer, caches, episode hash and credential persistence.
This is user hardware feedback, separate from controlled host measurements.

MDBList watched history was fetched only as a Continue Watching veto. It never
fed the movie badge map or episode watched index, and an empty Continue Watching
list skipped it entirely. Nuvio account history was also suppressed merely
because Trakt was enabled. Watched evidence must be merged independently of
the chosen Continue Watching source and playback-reporting consent.

Primary docs checked on 2026-10-09: https://api.mdblist.com/schema/ and
https://mdblist.docs.apiary.io/reference/sync/watched-history/retrieve-watched-history
The documented episode identifies its parent under episode.show, with
last_watched_at. Accept that and the current sibling-show/watched_at envelope.
Desktop 0.1.29-alpha, commit 80d8ce33d802ca24e162464350b146fcbbdd12a9,
MdbListWatchedDecoder.kt also supports explicit nested show.seasons episodes
(the seasons array is on the history row). A show/season activity timestamp
alone never establishes whole-series/season completion. Null timestamps do not
count. IMDb-backed titles are imported; TMDB-only records are skipped because
the existing native history maps would collapse their IDs to 'tmdb'.

Fetch a complete bounded snapshot on the existing background worker at startup
and every ten minutes. Prefer next_cursor; retain legacy offset/has_more support.
No since filter on the full import: years-old watched movies still matter.
Deduplicate exact movie/episode identities with a bounded hash; newer timestamps
win. Reject failed later pages, repeated cursors, malformed responses and bounds
overflow before publishing. Existing rate-limit/auth/network backoff applies.
The import performs GET only and never reports playback or writes account history.

Main-thread merges touch at most 64 indexed entries per frame; stable frames do
only revision/scope checks. Reconcile when another provider updates the history
maps, without catalogue traversal or changing progress rendering. Clear episode
and imported snapshots on account/profile boundaries, reject old credential replies.
Preserve explicit TV unwatch intent using the existing account/profile journal.
Confirmed unwatch tombstones survive prune/restart; a newer remote watch or a
later local gesture supersedes them. With Nuvio history upload disabled, record
local intent without queuing any account write. The journal remains bounded at
4000 entries; existing eviction rules apply. Preserve original Trakt dispatch.

Tests cover documented/modern/nested envelopes, movie and episode indices,
pagination/dedup, old history, failure retention/retry, stale profiles, quotas,
local unwatch/restart, no upload when disabled, and 10000 idle ticks with no
history traversal/network requests. Existing account and provider tests run too.
Native map limits remain 8000 episode states / 8192 title states. MDBList snapshot
is bounded at 16000 records / 32 pages; Nuvio retains its existing 2700-row bound.
These are positive-history imports, not a full remote-deletion journal mirror.
Real account acceptance of this follow-up still needs physical-TV verification.

### Installed update changelog (shared follow-up)

The MDBList channel embeds bounded public release highlights in the native core.
Use the compiler's NV_VERSAO for the installed version, never GitHub latest or
an unchanged Samsung shell version. The builder records the generated header's
SHA-256 in SOURCE.json. Keep this content public and free of credentials.

Only offer the changelog after Home is ready, login/profile selection is complete,
playback (including the mini player) is closed and other overlays have finished.
Consume modal input, suppress Home/trailers beneath the opaque card, and preserve
interface scaling. Text uses existing cached rendering, three bounded cards per
page, remote arrows and OK/Back dismissal. No blur, new assets or UI networking.

A single atomic app-private version marker is written on dismissal. Check it once
per process; failed persistence may show notes again next launch but must never
reopen repeatedly in the same session. About & help can reopen notes at any time.
Tests cover version changes, relaunch, failed writes, held-key repeats, page bounds,
10,000 idle checks and geometry at multiple UI sizes. The GLES fixture captures
all three pages from the actual generated notes; runner performance is not TV FPS.

The tenth patch additionally waits for Spotlight search, its keyboard and TV-guide
reminders. Route changelog input immediately after the emergency log handlers,
before notice/clock/global shortcuts: otherwise a background notice can consume
OK while hidden behind the opaque changelog. The actual app event router is tested
with both a notice and changelog present: OK dismisses the changelog, the notice
remains available, and Back then closes the notice. Patch 9 stays immutable after
its first LG publication; this interaction correction is an additive patch.

The actual GLES captures found the default art-derived accent can be near white.
White text on an accent-filled close button was unreadable. Patch 11 uses a dark
button fill independent of the accent, tests at least 4.5:1 label contrast across
dark/mid/pale accents, and separates the version subtitle from the large title.
Capture the actual page count; the builder keeps at most six highlights so the
standard release uses two balanced pages. Published patches 9/10 remain intact.

### Upstream 2.0.3: component adapters and compatibility quarantine

The LG scheduled run 37973930428 detected the stable 2.0.3 release but failed
before compilation: the original MDBList patch conflicted with five redesigned
Settings files. Samsung's workflow was active, but no run followed that release;
the six-hour schedules offered no prompt-delivery guarantee. GitHub can delay
or drop scheduled runs. Do not describe scheduled polling as an upstream webhook.

Both monitors now poll hourly at separate minutes, accept repository dispatch,
and run after integration/updater pushes. Detection paginates releases, excludes
drafts/prereleases and selects the highest numeric version independently for each
platform. Never assume GitHub's release-list order is version order. The LG app
also selects the newest numeric webOS package when its list is unsorted.

2.0.3+ uses integration/manifest.json: owned modules are copied with verified
digests; nine component adapters merge against the immutable 2.0.3 base. The
historical twelve shared/base patches and LG patch remain unchanged for release
audit. Settings' custom IDs, persisted keys, defaults and descriptors come from
one mdbsettings.def registry; the Tracking rows have an owned include. Keep the
section enum, preview artwork and help table aligned with the presentation map.
Coverage must prove every option appears exactly once. The 58 custom translation
entries merge by decoded key rather than patching 29 positional language tables;
preserve upstream native translations and reject changed owned keys explicitly.

Preflight applies every adapter, records its component/digest, checks interfaces,
validates Settings/languages, syntax-checks affected C modules and runs behavior
fixtures before installing a TV SDK or reading private build properties. Token
checks are diagnostics only: compilation and functional tests remain mandatory.
SOURCE.json records the exact upstream commit, component and overlay digests.
Do not declare compatibility from a patch applying cleanly.

2.0.3's durable unwatch judge must remain authoritative. Remote Nuvio/MDBList
imports use vistoep_fonte with the remote watched timestamp; vistoep_definir is
for local gestures. Retain the indexed map, revision caches, 64-row/frame merge
limit, profile isolation, scrobbling consent/threshold, installed changelog and
all prior cache/layout fixes. The map has one mutex; internal helpers called
under it must not lock it again. Test real pthread concurrency and both durable
unwatch and positive-history import behavior, not no-op mutex fixtures.

The first Linux preflight caught the upstream unwatch fixture's missing catalogue
revision doubles, then proved the old episode journal tombstones prevented the
new test from exercising post-prune protection. Keep durable journal tombstones
for whole-title/movie removals; prune confirmed episode entries only when a
matching vistonao guard protects them. Do not weaken the upstream post-prune or newer-remote-watch
assertions to make a port pass. Those assertions now run before every full build.

Upgrade fixtures must start with old persisted data, not only gestures created
by the new build. A pre-2.0.3 episode removal exists in the account journal without
a vistonao entry: normal 2.0.3 pruning would erase that intent. The optional
read-only handoff checks the journal's explicit account, profile, episode and
gesture time before pruning. No guard means retain the original entry and time;
a genuinely newer remote watch still wins. Test legacy prune/restart and new
post-prune protection together, including account/profile isolation. Do not
retimestamp old gestures, change the journal format or weaken either fixture.

Transport reads retry only timeouts, connection failures and HTTP 408/429/5xx,
at most three attempts with bounded backoff. Never retry conflicts, assertions,
compiler/linker errors, bad checksums, auth failures or changed contracts as if
they were transient. Public POSTs need reconciliation after an unknown result;
publication uses draft assets and verifies all checksums before making it live.

Failures produce a named compatibility report, Actions summary, diagnostic
artifact and deduplicated GitHub issue. Source/check conflicts are quarantined
by platform, upstream release ID and integration fingerprint: later polls skip
the expensive build. Changing the reviewed integration/updater or receiving a
new upstream release rechecks automatically. Manual force is for investigation.
Successful publication closes the matching issues. Failed updates never delete
or replace the last working release or weaken Samsung's shell/engine identity
gate. A changed host/resource/engine requires a newly signed full TPK install;
do not promise the old shell can accept an incompatible native core.

Regression coverage also exercises interrupted public uploads/draft creation,
refusal to modify live assets, notification deduplication/recovery, keyed label
collisions and archive checksum/path rejection. A failure to close an issue after
successful publication is a warning, not evidence that the live release failed.

The first complete 2.0.3 cloud builds exposed two infrastructure cases. Docker
BuildKit reports a rate limit as `unexpected status from HEAD request ...: 429`;
classify that exact form as transient, while a compiler/assertion/conflict in the
same output still takes precedence. Use the verified ARMv5 Debian manifest from
Google's Docker Hub cache to avoid shared runner pull limits. Generate a separate
SDK Dockerfile after validating the upstream FROM/architecture; leave the
upstream recipe unchanged and reject a changed base before the full build.

GitHub release creation can return 403 when an in-flight build targets a commit
whose workflow definitions differ from the current default branch. GITHUB_TOKEN
cannot receive the workflow permission needed to tag that older workflow commit.
Do not request a broader personal token or silently retag the tested artifacts
at an untested commit. Record the exact builder commit in SOURCE.json and the
release body; compare workflow tree IDs before publication. A changed workflow
produces a named, non-quarantined publication-stale notification and preserves
the last live release. A fresh run from the current default branch automatically
retries on the repair push or next hourly poll. Include public GitHub error
messages in diagnostics without printing request bodies or authorization headers.

Keep simulated failure reports isolated from the real Actions step summary.
Updater regression fixtures must temporarily disable GITHUB_STEP_SUMMARY and
restore it before production preflight. Otherwise a successful LG/Samsung run
can display an invented Settings conflict or quarantine notice from a test.
Verify the existing summary stays unchanged while the complete updater suite
runs; real compatibility reports and failure notifications remain enabled.

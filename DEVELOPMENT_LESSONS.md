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

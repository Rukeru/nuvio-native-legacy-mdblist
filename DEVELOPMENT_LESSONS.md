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

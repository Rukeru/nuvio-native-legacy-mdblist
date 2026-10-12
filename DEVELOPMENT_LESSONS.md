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

### Upstream 2.0.4: preserve upstream tests and review every adapter

Issues #7/#8 stopped at the first overlapping insertion in
tests/ajustes_padroes.c. Upstream added factory-default/local-scope/display-order
checks for automatic subtitle sync at the start of main, where our five MDBList
assertions had been inserted. This was a source merge conflict, not a failing
assertion or scheduler failure. Never remove the new assertions or disable that
test to obtain a green build.

The owned tests/mdblist_settings_defaults.c includes the unchanged upstream test
with its main renamed, checks all five original MDBList assertions, then executes
the real upstream main. Its portable runner uses actual application sources and
keeps assertions enabled. This companion is shared between Tizen and webOS;
upstream factory-default tests no longer carry our insertion patch.

Resolving the first blocker also exposed native Settings additions and a season
chart cache edit. Preserve source-order and automatic subtitle-sync declarations,
defaults, keys, categories and help alongside the owned settings registry.
Retain both the upstream canonical episode-suffix fix and the custom per-title
revision/snapshot cache; replacing it with a global watched revision would undo
the performance fix. Coverage now checks 264 options in 12 categories and 5432
language keys, and the indexed map retains upstream's forward-unwatch/batch API.

Rebase reviewed adapters on immutable 2.0.4 commit
db6ae4ee0dd2fa158c46ba375c1fe8c08de70504, regenerate every patch SHA-256 and owned
file digest, repack the checked integration archive, and reconstruct both
platforms from clean checkouts. Historical 2.0.3 releases/source archives remain
available. A clean patch application alone does not establish this new baseline.

Run the upstream tools/testa-tudo.sh gatekeeper suite on its native macOS host,
plus the existing MDBList/account/history/concurrency and real GLES rendering
checks. Both publication jobs require the full regression job and the actual
platform build to succeed. Retain the upstream runner's explicit unavailable/
non-gating classifications and logs; never count SKIP as tested or reinterpret
a skipped build as a published release. No Cloudflare, Sync Now or support UI
work belongs in this compatibility change.

Bind full-suite evidence to the exact upstream commit, builder commit and
integration fingerprint used by the package. Attest the real upstream summary
and require the owned defaults test to pass; a missing summary, all-skipped run
or different source cannot authorize publication. Linux-only GLES fixtures are
explicitly unavailable on the macOS host and are mandatory in both Linux
platform jobs. Select the equivalent Darwin/Linux dead-section linker option
for portable fixtures without changing their assertions.

Normalize deployed Bash files to LF before browser/API uploads from Windows.
An upload preserves raw CRLF bytes even when local Git would normalize them;
`set -euo pipefail` then becomes an invalid option on the runner. Declare
`*.sh text eol=lf` and verify actual deployed script bytes in updater tests.
Source assembly passing does not prove the preflight script itself can execute.

The complete upstream suite also compiles isolated discovery and addon fixtures.
Extend their explicit service interfaces rather than removing cases or linking
uncontrolled account/network services into them. Disabled MDBList discovery
fixtures reject unexpected library requests with assertions; header-aware addon
fixtures delegate to their original controlled downloader and assert that no
unconfigured proxy headers were supplied. All original assertion counts remain
unchanged. Install ripgrep/coreutils on the native runner and replace developer
SSD output paths with unique temporary paths; these are harness adaptations,
not changes to the tested behavior.

The expanded suite also checks exact enum boundaries and an explicit icon for
every visible row. Preserve upstream ID adjacency, assert the exact seven-ID
owned suffix and final boundary, and supply the real icon mappings for those
rows. Do not replace boundary assertions with inequalities or exempt custom
rows from the existing visual-map test. Check registry/icon coverage before SDK
setup so this presentation mismatch cannot hide behind a successful build.

Distribute the full gatekeeper enumeration over isolated native runners to avoid
one long serial job timing out. Preserve the original test scripts, exclusion
logic and exit/SKIP rules. Verify each assigned script was visited exactly once,
every shard used identical source/builder/fingerprint and gatekeeper, every
summary checksum matches, and all shard totals cover the full inventory before
attestation. Failed/missing shards cannot be treated as partial success. Only
allocate native regression runners when the inexpensive Linux release selector
finds an update; unchanged hourly polls must not consume macOS build minutes.

Provision the original Kotlin JVM fixture with pinned, checksum-verified Maven
dependencies and actual WASM fixtures with the pinned official Emscripten SDK.
Supply only the previously authorized shared app build configuration to account
tests, keep it outside uploaded evidence, and remove it even after failures.
Name dependency/setup failures separately from source compatibility failures.
Any FALHA result or Darwin undefined-symbol failure suppresses whole-command
retries even if another line mentions a transient HTTP error.

Compare unexplained graphics/texture failures with the exact unmodified upstream
commit before changing application behavior. The 2.0.4 baseline diagnostic
reproduced failures in ilha_voo_cw, spainel_fundo_tempo, texbruto,
streamfit_sheet and trailer-hero-contract without any MDBList integration.
Fixed-dt animation fixtures must use the same frame timeline for deadlines:
software-renderer wall time is not a 16 ms animation step. Preserve every
frame, geometry tolerance, pixel threshold and reconstruction assertion. Run
the real GLES renderer fixtures on Linux, and retain the original Darwin path
for local use. CPU mipmap coverage uses ASan plus UBSan on native SDL2/Linux;
the original Guard Malloc path remains available on Darwin.

Initialize real SDL timers in stale-texture fixtures before recording a request:
zero is a reserved "no request" timestamp. Isolated source-selection fixtures
must explicitly configure their unfiltered setup when the application default
filters uncached sources. Give new setting categories distinct preview scene
identities and unique real art mappings, rather than relaxing the existing
cross-category uniqueness checks. Track shared fixture includes as checksum-
verified owned modules and keep all native platform adapters in one registry.

Host library/toolchain differences are test setup requirements: GNU C++ is
required to exercise both libstdc++ string ABIs; Darwin uses DYLD_LIBRARY_PATH
and its actual pinned FFmpeg pkg-config private dependencies. Provision the
exact dotnet SDK, mkvmerge, OpenSSL, Playwright, Kotlin and Emscripten required
by assigned tests. Loopback fixture servers must not depend on reverse DNS for
their diagnostic server_name; sockets, client requests and TLS assertions stay
real. Do not upload temporary compilers, binaries or shared app configuration
as regression evidence. Upload complete logs and provenance, and require every
assigned script to be accounted for before authorizing either release.

The extended 2.0.4 suite exposed additional fixture preconditions and two
integration regressions. Preserve source transfer safety (`foraCache`) independently
of strict cache metadata (`cacheEstado`): a name-based uncached hint must still
protect transfer limits without admitting unknown sources to cached-only results.
Assert explicit metadata precedence and both original transfer/quota behaviors.
The context-menu information-side getter must report the side of the information
panel, which has opposite sign to the morph menu side. Retain the original
geometry assertions rather than changing their expected side.

Settings preview ownership needs a semantic contract, not just row counts.
Validate contiguous scene ownership in basic sections, the dedicated MDBList
scene, season-number placement, and all advanced references before compiling.
Restore the existing discovery milestone only when the generation/owner guard
actually publishes the partial catalogue. The unchanged upstream progressive
fixture passes on 2.0.4; its integrated failure is not an upstream baseline waiver.

Never use unresolved-symbol dynamic lookup to make a fixture link: it can turn
a missing boundary into a runtime null call. Link reachable real ranking/parser
modules and give disabled optional services explicit, asserting interfaces.
Keep upstream codec-negative coverage using genuinely invalid metadata and add
exact positive payload assertions when upstream adds AC3/EAC3 support. Preserve
the original art-lighting checks and separately assert new logo-lighting behavior.
Real SDL timers, initialized demo-player state, explicit unfiltered source setup,
and a GOP matching the HLS fixture segment duration are setup contracts; original
timing, geometry, pixels, throughput, transfer and lifetime thresholds remain.

Provision the actual legacy Node engine, complete Kotlin compiler runtime,
matching dotnet SDK and real pinned P2P engine rather than recording their absence
as verification. Full current-source WASM glue includes animated WebP and libass.
Long renderer measurements retain every scenario, frame and sample. Report
fixture-log growth and use line-buffered benchmark output; run fast assertions
before the full WASM build and all-scenario measurement. Diagnostic runs of
unmodified upstream explain failures but never authorize either platform release.
Local adapter replay, native syntax/link checks and individual fixtures are
intermediate evidence. Establish the baseline only after both full platform
workflows validate and publish the exact source and integration fingerprint.

An unchanged-catalogue rendering fixture must provide complete local metadata.
The saved-panel fixture used real IMDb identities with empty synopses: hero
prefetch successfully filled two descriptions from public services, legitimately
changed the catalogue revision, and broke five zero-reconstruction assertions.
Provide local synopses for every fixture item instead of disabling metadata
fetching in production, ignoring revision changes, or adjusting expected counts.
The original idle/navigation frames and every cache/pixel assertion stay intact.

Host-engine verification also needs one consistent C++ toolchain. The pinned
engine uses C++20 stop tokens/jthreads, unavailable in the runner's default
Apple library. Probe those features with the selected GNU C++ compiler before
building; give CMake, the engine PoC and the real lifecycle fixture that same
compiler/linker. Keep the engine source pin, real libtorrent, native lifecycle
assertions and production platform engine builds unchanged. Setup failures must
block release, never become a SKIP or be retried as transient network failures.

Check fixture encoder capabilities before executing media cases. Current minimal
Homebrew FFmpeg lacks libaom-av1, so a successful H.264/VP9 run cannot stand in
for AV1 byte-equivalence coverage. Select the native FFmpeg 7 CLI encoder set
(https://formulae.brew.sh/formula/ffmpeg@7), verify every required encoder and
use its paired ffprobe. Keep the decoder being tested on the upstream-pinned
minimal FFmpeg source and preserve all codec, downmix, range and sparse-seek
assertions. A missing codec is a setup failure, never a reason to skip a case.

Preserve the verified Emscripten SDK path across sourcing emsdk_env.sh: its
construct_env cleanup clears unrecognized EMSDK_* inputs, including EMSDK_DIR.
Restore the saved path before
invoking child WASM build scripts so they do not fall back to an absent
developer HOME installation. Keep the real libass/WebP builds and all original
Node 10 page/worker and modern-engine controls; do not substitute synthetic glue.

Specify ranking preferences when testing raw autoplay independently of sheet
ordering. Upstream balanced mode applies measured bandwidth penalties; maximum
quality preserves the original raw winner. Configure maximum quality for the
original unchanged-winner assertion and separately assert the exact balanced
winner with the same real ranking code and measurements. Preserve every source
identity, stable group, focus, frozen-photo, incremental and duration assertion.

Name sourced setup includes with .inc rather than .sh. The upstream gatekeeper
enumerates tests/*.sh: a setup-only include would otherwise inflate its passing
test total without executing assertions. Keep every real test in the inventory;
exclude helpers by their source-file role rather than changing gatekeeper rules.

When a fixture opens extra menu modes directly, deliver the opening gesture's
KEYUP before exercising action buttons. ctx_abrir_salvo intentionally consumes
that release; omitting it leaves the next OK swallowed. Retain the original
hold/repeat, removal, catalogue-copy, focus and geometry assertions, and test
both inline production mode and floating legacy mode explicitly.

The incomplete-page fixture deliberately has no local pending journal or legacy
saved entries. Define that boundary explicitly for sync completion, assert that
unexpected migration/item reads do not occur, and strictly link every reachable
interface. Keep real journal/migration modules in their dedicated suites. Declare
the POSIX feature level before headers when using mkdtemp in the availability
fixture. Real TS-proxy timing/byte assertions run on the supported Linux host;
retain their deadline, throttle, header, PAT, redirect and encryption checks.

Tool discovery must recognize quoted SDK executable paths as well as bare emcc
commands and environment activation. The memory fixture invokes its SDK path
directly and was missed by the old assignment/command regex. Cover that exact
form, activated compilers and ordinary native-only fixtures in updater tests.
Conservative provisioning is preferable to omitting real memory/worker checks.

The 184403e full regression round proved the real GNU P2P engine and the Linux
proxy, saved-panel and progress fixtures, but exposed later player and timing
contracts. Upstream #305 hides and reveals controls on repeated Up; model that
complete sequence and retain the original focus/no-audio assertions, adding
explicit visibility assertions. In balanced source mode, measured heavy sources
lose to equal-score adequate/unknown candidates; equal scores retain add-on
arrival order. Assert scores and the tie winner rather than guessing an index.

Loopback range fixtures should disable Nagle on their HTTP/1.1 origin: explicit
20/800-ms fixture delays must not silently acquire platform delayed-ACK stalls.
Retain the original four-second prefetch deadline, serial/parallel lanes, bounded
queue, byte identity, seek and cancellation assertions. Native lifecycle mocks
should reserve timer-worker capacity and buffer host stdout away from watchdog
callbacks. Retain every original fatal/cleanup assertion and timing threshold.

Use the read-only manual compatibility diagnostic to execute complete affected
fixtures against the immutable upstream source, optionally applying the verified
current adapter. It records individual pass/fail logs and checksum evidence,
and cannot publish or replace the full nine-shard release gate.

Focused diagnostics revealed that keyboard Up consumes the previous rendered
skip-intro snapshot, which must be supplied through the existing upstream shot
hook. Exercise both a visible intro and no intro, retain every focus/audio
assertion, and cover hide/reveal explicitly. The final movie button exists only when related metadata is available. Explicitly
provide zero related titles for the original Sources check, and add a controlled
related-title case to assert the new panel behavior.

The short-tap/long-hold saved-panel fixture uses fixed 1/60-second animation
updates. Drive its SDL deadlines with the same atomic fixture clock: two slow
CI render frames must remain a short tap. Keep the actual hold threshold, every
frame, all removal/focus/geometry assertions and real rendering. Darwin declares
mkdtemp in unistd.h; feature macros alone cannot supply a missing declaration.
Include the actual platform header alongside the POSIX feature level. See
https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/mkdtemp.3.html.

Run the complete .NET lifecycle deadline fixture on Linux, as with TS-proxy and
other portable timing fixtures. The Windows .NET 8.0.425 check passes every
original deadline; macOS host scheduling can delay its timer beyond 250 ms.
Keep all deadlines and fatal/cleanup checks unchanged on the supported Linux
host, prove inventory assignment exactly once, and require that shard's result.
The focused diagnostic uses that same host and the same fixture DNS boundary.

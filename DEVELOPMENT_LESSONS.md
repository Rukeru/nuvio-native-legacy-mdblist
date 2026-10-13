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
the performance fix. Coverage now checks 264 options in 12 categories and 5437
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

The availability fixture must pass dados_dir() to Settings after dados_iniciar:
NUVIO_DADOS intentionally overrides its fallback directory. Writing through the
data API and reading a different raw path silently restores cached-only factory
defaults. Verify the saved file contents and the disabled-filter precondition,
then retain all original service-row, raw-index and partial-list focus checks.
The complete player regression at d364d66 passed every original and added check.

The 529fd8d full webOS shard exposed two scheduling-dependent preconditions
that focused checks had not established. hero_vizinhos expected the urgent
request to finish between two neighbour downloads, but the worker had not
started either neighbour: urgent-first was correct. Add a bounded condition
barrier proving that a neighbour is in flight before queuing the urgent request.
Retain the original download ordering, cache, no-extra-network and subsequent
neighbour warming assertions; do not change production priority policy.

The complete serial DTS prefetch test intermittently exceeded four seconds on
macOS despite passing focused runs with TCP_NODELAY. Keep its four-second
deadline and every byte, bounded-queue, sparse-offset, seek/cancel and serial/
parallel case unchanged on Linux. Build the same source-pinned minimal FFmpeg
7.1.5 decoder and verify every real CLI encoder before testing. Provision Linux
libraries before dependency discovery; never call Homebrew on Linux or replace
missing codec cases. Cover both the real build selection and missing-encoder
rejection in updater tests. Publication still requires both complete new suites.

The later full context-list fixture exposed the same fixed-dt/wall-clock mismatch
as the saved-panel hold fixture. Slow catalog rendering postponed the threshold
update, so the test seeded menu metadata before the menu existed. Drive quadro
with the existing atomic fixture clock before reading agora or routing events.
Keep the actual hold threshold, two-frame tap, all catalog/collection/search
paths, every geometry/focus/metadata assertion and real render captures.

The bfe422d full shard found an intermittent retained-player fixture race. The
previous close really rebuilds Continue Watching on a background worker; its
publication can replace catalog index 0 between the next one-item setup and
player_abrir. A channel scenario then opens the preceding movie. Before each
new setup, wait at most two seconds for the real discovery publication to be
quiescent, then assert the catalog type and the frozen player channel flag.
Retain every original suspension, identity, source-cache, load/stop/seek and
120-second expiration assertion. Do not mock away catalog publication or alter
production suspension rules to make a scheduling race pass.


## Published 2.0.4 baseline and release freeze

On 2026-10-12 both platforms published immutable upstream source
`db6ae4ee0dd2fa158c46ba375c1fe8c08de70504`, builder
`e6ff0b442e9b753c07c3d712eb19cc8cc3c1775f`, and integration fingerprint
`0ffdd4542d3c3162f2dea23c15b361e993bc8d172256a6b7b0cc17b6552f1b15`.
Tizen `v2.0.4.63` (run 38254860753, attempt 2) and webOS
`webos-v2.0.400059` (run 38254860865) each attested 470 passed, zero failed,
zero unverified skips, and 107 original upstream gatekeeper exclusions.
The published SOURCE.json identities match the complete nine-shard attestations;
both 2.0.3 releases remain available. This is the next development baseline.

After a user-requested release freeze, allow both workflows to finish on the
same commit. Do not push speculative repairs or restart successful validation.
The final Tizen assertion was `streamfit_redirect_range.c:24`, four-connection
average >640 kbps; the failed run measured 600 kbps. Its unchanged fixture and
production source passed three isolated repetitions at 956, 956 and 964 kbps,
and the complete related diagnostic passed. This supports a timing-dependent
failure, not a proven production conflict. Do not describe TCP_NODELAY as a
proven repair: that comparison was not performed and no transport patch was
merged. A single retry of failed shard 6 then passed all 60 required tests;
the eight successful shards and native package were retained. Aggregate and
publication gates ran normally, verifying exact source and complete coverage.

Before retrying a job, inspect artifact naming. This upload-artifact revision
uses immutable names and defaults overwrite to false. The existing failed
`tizen-regression-shard-6` artifact would conflict with the retry. Preserve and
SHA-256-verify its complete archive before requesting explicit permission to
remove it. Only that backed-up failed artifact was deleted, with user approval;
job logs and successful artifacts were retained. Future workflow optimization
must preserve attempt-specific evidence, select results by validated provenance,
and retain every required test, inventory check and publication gate. Never
retry a genuine source/assertion conflict without focused evidence, or count a
cancelled/skipped workflow as successful validation.

Upstream 2.0.4 changed the Samsung host/resource identity from
`d0b3c621791d8d991ea54a537e98a2f03037c36a184792bfe7dd4842fc392885` to
`616bc9052b5eac94bd9c1ae8dc1b581f8880ffd0056e28bad7b0bb5ace0af6cf`.
Preserve the compatibility guard: this transition requires signing/installing
the new complete TPK rather than hot-loading its core into the older host.
CI validates integration, account/tracking fixtures and rendering/performance
contracts; it does not attest physical-TV playback or a private live account.

## Measured CI optimization, 2026-10-12

Profile completed jobs before optimizing. Runs 38254860753/38254860865 took
201.77/104.30 minutes end-to-end and 337.75/312.93 actual runner minutes.
The Tizen elapsed figure includes investigation and a delayed same-source
retry; it is not a pure machine-performance baseline. Deduplicate retained
successful jobs by name/start/end timestamps when reading later attempts.
The longest single queue delays were 69.85/53.75 minutes. Homebrew normally
took 18–49 seconds, whereas Linux regression took 52.85/50.62 minutes and
the separate UI comparison about 15 minutes. The complete performance fixture
took 28–30 minutes, preceded by about 20 minutes of unrelated Linux work.
Move that entire fixture to its own equivalent runner, not to fewer frames,
weaker deadlines, or a substitute benchmark.

Most host fixtures compile the same full C application repeatedly. ccache does
not cache a multi-source compile/link invocation directly. The narrow opt-in
`ci_compile.py` wrapper separates ordinary translation units, bounds compilation
to two processes, and preserves link order/flags. Unknown commands pass through.
Use compiler-content checking and preprocessing; do not enable cache sloppiness.
Validate ccache configuration before a fixture: `CCACHE_DIRECT=false` is invalid;
its supported disabling variable is `CCACHE_NODIRECT=1`. The initial focused
experiment exposed that configuration error; no application assertion failed.

Corrected run 38288091744 at 9798b32e2ba3f1a6cba0f2b7750b7f59e10b1be6 passed
three unchanged fixtures in original/cold/warm modes on each host. macOS sums:
153.34/122.89/29.41 seconds (19.9% cold, 80.8% warm improvement). Linux sums:
188.22/125.91/55.49 seconds (33.1% cold, 70.5% warm improvement). Entire comparison
jobs took 5m54s/6m54s including all three executions and setup. These measurements
prove a fixture speedup, not the elapsed time of a full release. Uploaded evidence
SHA-256: macOS b63de908531a9a713baefee3296d851a94df10ac8213486b69eb0a2a8fffe328;
Linux 1d86648c38f405dda47626eeb1defb4fa416d505f5a0d24ef413ab0faddab31f.

Keep development pushes separate from full release dispatch. Ten-shard scheduling
retains the eight macOS partitions and splits the original Linux partition into
the benchmark and all other fixtures. Inventory/attestation must still account
for every script exactly once and reject every unverified skip. Replayed baseline
archives test aggregation only: they are not newly executed application tests.
Validate the new infrastructure once with nonpublishing full-suite evidence,
then record its actual timing before claiming an end-to-end improvement.

Attempt-specific artifacts prevent immutable-name collisions. Never merge their
directories blindly or fall back to an older pass when the latest attempt failed.
Match run, source, integration, gatekeeper, inventory, checksums and per-shard
compiler/dependency/runner-image identity. Retain failed and setup-incomplete
archives. Only a later complete attempt may supersede incomplete setup evidence.
Diagnostic-only CI evidence must never authorize package publication.

The complete nonpublishing proof (38289570135, commit
137a05c5eb124b34b5d2d383d5b58cb35c20da56) finished on its first attempt:
470 passed, zero failed, zero unverified skips, 107 original exclusions,
577 scripts accounted for exactly once. Archive SHA-256:
c31aa8302b0d6544edcf40303a09e7fa501b667a7ff8192298eda488e2b23722.
Regression-only elapsed time was 54m38s versus 103m27s in the prior webOS run;
actual runner time was 195.42 versus 283.88 minutes (31.16% less).
Summed test execution fell from 252.60 to 163.67 minutes (35.21% less).
Summed per-job queue time fell from 207.55 to 66.77 minutes; that is not
additional elapsed time. The old run competed with the Tizen release, whereas
the proof ran one platform, so do not attribute its entire 47.19% elapsed
reduction to caching or extrapolate it to a complete two-platform release.
Dependencies took 5.67 versus 5.62 runner minutes; toolchain provisioning
15.78 versus 16.70. These were not the main compilation savings.

The full performance fixture still took 28m53s, with every original workload.
The longest macOS shard took 25m38s testing plus roughly eight minutes of SDK
setup and started nineteen minutes late. Submit that measured longest shard
early without changing its membership or checks. The scheduling reorder's
additional benefit is not measured yet; validate it in the final feature
release, not another workflow-only full run. The 30–45 minute complete-release
target is not yet demonstrated. Native packaging was deliberately not repeated
in this infrastructure proof. Fast development run 38289570079 passed in 9m22s.

## Private diagnostics development boundary

Keep maintained backend sources under `private-diagnostics/`: `diagnostics/`
already belongs to the updater's generated compatibility/error evidence.
Backend-only changes select the Node security/runtime gate and never native
TV validation. The backend has an independent versioned protocol and does not
change the application's integration fingerprint on backend-only source edits.
Both publication workflows nevertheless require its security gate to pass on
their exact checkout before publication.

Test the actual Workers runtime as well as SQLite behavior. A deployable Worker
entry point must export its handler, not test-only constants; keep protocol
helpers in a separate module. Use Wrangler's SQL splitter for multi-line D1
migrations and triggers: D1's exec API splits individual lines. The 19 focused
tests cover real workerd/D1 execution, atomic quotas, enrollment response loss,
concurrent claims/delivery, token rotation/revocation races, retention and strict
privacy rejection. These local passes do not attest a production deployment.

## Private diagnostic client development

Keep the private client in owned `nvdiag` modules and a separately diagnosed
`private-diagnostics` adapter shared by both platforms. Do not globally replace
`NV_REC_URL`: unrelated social functionality still uses it. Remove legacy raw
diagnostic transport paths, including startup and optimization-report uploads.
Local logs and optimization reports remain local; submission requires the
structured preview and explicit Send action, or fresh recipient-specific opt-in.

Use the existing bounded `rede_pedir` API with authenticated TLS, redirects off,
4 KiB response/header limits and a 10-second deadline. The older generic POST
wrapper does not provide these safeguards. Persist only typed numeric events,
revalidate them before serialization, and cap queue size and retry attempts.
Generate device secrets with OS entropy, save them owner-only before enrollment,
and never reuse account credentials. Preview/status getters must not read files.

New diagnostics coverage is added inside the existing custom fixture script,
preserving the complete upstream script inventory and shard membership. The
independent Worker schema validates every client event in the fast Python gate.
At this development checkpoint, 66 updater/protocol tests and fresh source
integration contracts pass for both platforms. Native client fixtures are still
pending at that checkpoint; production transport remains disabled.

## Live Cloudflare deployment and diagnostic review

The first native client development gate passed for both platforms on
`a4dd1afa8f003950df940af7ea216ef478171d8b` (run 38300150826): Tizen 3m48s,
webOS 4m38s. These are focused development results, not full release proof.
Subsequent observer and consent-race changes require their own focused gate.

Browser login does not authorize Wrangler. Use the explicit Workers Scripts
and D1 scopes; general `workers:write` returned no access to deployments.
Device OAuth avoids inaccessible localhost callbacks. Never expose tokens or
commit the local authentication/configuration files.

Production D1 rejected trigger SQL that passed SQLite and local workerd.
Formatting BEGIN/END on separate lines and parenthesizing CASE expressions,
without changing quota semantics, allowed the remote migration to pass. Add
LF policy for SQL files and retain the original quota/concurrency assertions.
See Cloudflare workers-sdk issues #14991 and #4727 for the parser class of
failure. Local runtime validation cannot stand in for a live migration check.

Twenty-one authorized synthetic live checks passed, including both platforms,
private D1 persistence, idempotency, schema/size rejection and revoked tokens.
The test helper revokes in finally and emits no credentials. Ingestion was
disabled again afterward while app consent and final release gates remain
pending. Record immutable deployment IDs separately from application proof.

Freeze a copy of the preview at the Send action, not when the worker eventually
processes it. Track the current manual report ID so an older or automatic
receipt cannot label another report delivered. Opt-out must cancel an active
automatic request, not merely prevent the next queue insertion. Test lost
pairing responses with the same persisted secret. Keep optimization reports
local and route their manual action to the same explicit sanitized preview.

## Account refresh investigation

The manifest cache used only URL and addon-list version, so a server-side
manifest change at the same URL could remain invisible indefinitely. Refresh
it after five minutes or an explicit Sync Now, retaining the last response
only as a labelled failure fallback. Fence writes by cache generation so a
request started before invalidation cannot repopulate fresh state.

The legacy sync completion tick also advances for interrupted/cached cycles.
Keep its scheduling contract separate from new per-account/profile freshness
and last-success state. An initial cycle stopped by the cloud circuit breaker
must become eligible for periodic retry after recovery. Manual refresh uses
the existing full worker and pending-local merge rules, never the login/profile
reset function that clears pending Settings writes. New fixtures exercise real
production C on both platform definitions; native results remain pending at
this checkpoint. The prior diagnostic fast gate passed both platforms and the
backend security job in run 38303162503 on acec078.

The account/manifest focused gate then passed on both platforms at 9930ac5
(run 38304378573). The new fixtures compile and execute the real sync and
discovery cache C for both NV_TPK and NV_WEBOS. They preserve the unchanged
upstream addon-sync harness and add initial-breaker recovery, fresh/cache state,
one-minute manual throttling, failed local-setting pushes, profile isolation,
five-minute manifest expiry and stale-request generation checks.

When removing Support the Project, retain its enum/default/persisted-key slot
as an inaccessible tombstone. Remove the navigation row, panel implementation,
search keywords and exclusive automation route. Replace assertions for the
removed product behavior with absence/route/focus assertions; retain all
surrounding persistence and navigation coverage. The historical standalone
release-card fixtures stay intact; custom app startup must not open their old
donation onboarding after its installed-version changelog. Copyright, licences,
the user guide and unrelated help stay available.

Add a focused macOS Settings/account gate for real interaction, offline,
Collections and manifest-wait fixtures. Cache compiler objects by checked source
content; these results remain development evidence, not release attestation.
The final live Worker source passed 21 synthetic checks on deployment
16db59eb-60bd-425e-817e-e0b64adeb921; credentials were revoked and ingestion was
disabled again (030fd652-6fc1-4564-b25a-fa713ed0baff). Build-time activation now
requires the reviewed backend/client/consent input hashes and live evidence.
Changing those inputs fails closed and requires re-verification. Per-device
pairing and fresh opt-in still apply after activation.

The first broader Settings/account gate caught compile/link errors before any
full release suite was launched (run 38305387969). Remove the legacy QR preview
as well as the new modal when retiring donation UI. Screenshot-only hooks are
behind AJUSTES_TESTE; ordinary interaction fixtures must assert real navigation
state instead of calling an unavailable capture hook. On Apple hosts, optional
external symbols require weak_import; ELF weak declarations alone do not allow
missing fixture providers. Keep the TV declaration unchanged and use the
portable optional-declaration macro in all adapters. The failed fixture logs
are preserved in artifact 11771932734; no full release runs were restarted.

Review also found two ways to mislabel a partial pull as fresh: perfis_puxar
returns its cached count after a failed request, and addon pulls return zero
for permanent HTTP failures. Add an explicit profile-read freshness signal and
preserve the previous successful timestamp for these failures. Reset manifest
failure/fallback status for each discovery refresh so later recovery clears it.

### Focused Settings and host-link boundaries (2026-10-12)

The 5940593 focused run exposed an outdated seven-entry custom Settings count after three appended entries. Keep every upstream-prefix and custom-index assertion, explicitly enumerate the new tail and assert its exact terminal count. `uxSecaoDe` returns category zero when absent; removal tests must exercise `focarOpcao` and assert unchanged focus, alongside zero navigation rows and no search results.

Mach-O still requires absent weak imports to resolve at link time. Isolated Apple fixtures now have weak fallback definitions, overridden by real strong providers when linked; ELF TV behavior is unchanged. Verify the strong override explicitly. The manifest worker cache fallback makes the existing late-refresh branch reachable to the linker, pulling the entire app into a small unit fixture. Inject only that outer refresh callback; retain every original cache/worker assertion and additionally assert one late notification and retained cache. Full app builds retain the real callback. These are focused failures; no full release gate was launched or cancelled.

### Retry reservation race and release-freeze correction (2026-10-12)

Final review found queue[index].attempts incremented outside the mutex although the Send action reads it under that mutex. This is a C data race even if individual aligned integer accesses happen atomically on a TV. The initial candidate was frozen too early; release runs #65/#61 were cancelled with explicit user approval before publication. Reserve attempt count and deadline under the same mutex, then release it before persistence and transport. The existing real-client C fixture asserts mutex ownership during reservation on both platform definitions; an isolated negative-control copy restores the old ordering and must abort at that exact assertion. No retry limit, performance threshold, consent requirement or test inventory was reduced. Complete concurrency review before the next freeze.

### Full candidate host/consent audit (2026-10-12)

Full runs 38309014776/38309057352 on a5d1da8 exposed gaps in the focused impact gate. They were left running to collect all results, with no intervening commit or speculative full-suite restart.

* macOS shard 6: `tests/nvdiag.c` used POSIX feature selection that hides Darwin's `mkdtemp` declaration. Add `_DARWIN_C_SOURCE` before all headers on Apple. Execute the complete `tizen_improvements.sh` in the focused macOS gate, including both platform definitions and the retry-race negative control; Linux-only success is insufficient for host portability.
* shard 2: a Windows text edit decoded UTF-8 `sync.c` as CP1252 before saving it as UTF-8. This corrupted both old and new translation keys. Reverse only the proven reversible encoding transformation and require `tests/i18n.sh` in the focused gate. The original source audit now reports zero missing keys on both fresh integrations; every locale/order/format assertion remains. Always specify UTF-8 for source reads and writes. Keep icon identifiers outside translated-label arguments to avoid treating `aj_send` as displayed text; do not suppress the audit.
* shard 1: `ajustes_envio_auto.c:57` still required the old upstream default-on/migration policy, contrary to the explicitly requested new-recipient opt-in. Preserve all scenario coverage (one-time legacy migration, missing/off/on stored choices, repeated Settings opening, enabling, disabling and restart). Assert that none of the legacy choices grants private consent, then exercise the actual default-decline UI, explicit acceptance, real worker persistence and restart. Test the independent consent file instead of pretending the legacy slot authorizes a different recipient. No product default is relaxed to satisfy an outdated expectation.
* Tizen shard 2 also reported an external Seekr DNS timeout while the identical webOS live fixture passed. Preserve this evidence as an infrastructure failure; do not change its assertions or call an unavailable network test successful.

Run the expanded focused host checks before freezing the repaired candidate. Passing integration/Python checks are not a substitute for native execution; the complete release inventory and both packages must still pass on the final revision.

### User-requested diagnostic disablement (2026-10-12)

The user asked to disable log tracking rather than delay the release further. Production diagnostic capability is now explicitly false even with historical security verification. In that configuration the client compiles inert APIs: no worker, event queue, private files, pairing, consent or HTTP calls. Observer macros do not evaluate their arguments; dedicated per-frame and memory-reporting hooks are compiled out. Cloudflare ingestion stays disabled and must not be enabled as the final release step.

The four upload/automatic-report/pairing/status Settings rows are removed while their enum and persistence slots stay reserved. Consent and manual-upload entry points remain closed. Focused navigation tests assert absence, inactive routes and unchanged focus. A native disabled-client fixture links without filesystem, network, formatter or pthread providers and exercises all public APIs on both platform definitions. Retained security/consent fixtures explicitly enable their isolated test implementation; they never activate the shipped app. MDBList/Trakt watch tracking, Sync Now, crash recovery and existing on-device troubleshooting remain separate and unchanged.

Update embedded release notes and user documentation to state the disabled status. Future automatic upstream integrations must preserve this explicit policy, not infer activation from a previous successful backend verification.

The same webOS candidate also reproduced the previously observed local redirect-throughput flake: `streamfit_redirect_range.c:24`, four connections measured 575 kbps versus the unchanged >640 kbps assertion. Add the original fixture and two isolated repetitions to the focused host gate, retaining separate logs, before making any timing or networking change. Do not lower the threshold or hide a failed repeat. Because the user explicitly changed the requested candidate to disable diagnostics, its focused development branch may run while the existing immutable full jobs finish; main and the full release candidate remain untouched until focused validation completes.

Focused run 38313371986 passed every modified native fixture on Linux and macOS, including diagnostic disablement, actual consent persistence, Settings routes, account refresh and i18n. Its only failure was the local redirect server producing no port file, then `n >= 2` at line 22 (not the earlier throughput assertion). The focused workflow omitted the existing full-suite `PYTHONPATH=upstream/tests/stubs/host` setup: that helper only supplies HTTPServer's loopback diagnostic server name, avoiding hosted reverse-DNS startup stalls. Align that environment; leave client DNS, sockets, TLS, request deadlines, server pacing and all throughput assertions unchanged. Retain the complete failed focused artifact 11776425405. This correction changes only the focused workflow, not app source or its bundle.

### Freeze upstream identity as well as the builder (2026-10-12)

The diagnostics-disabled candidate passed its focused 2.0.4 checks, including three unchanged redirect-throughput runs (38314750327). Release runs 38315569520/38315619169 then selected newly published upstream 2.0.5 and correctly stopped at the account-history compatibility guard before compilation. Freezing the builder alone did not freeze the intended upstream input. No release was published, and skipped aggregation/publication is not validation.

Manual feature releases now have an explicit reviewed-baseline input, shared by native-build and regression selection on both platforms. It fetches the exact published stable tag recorded by the integration manifest and carries its reviewed commit into the existing checkout identity guard. A missing, draft, prerelease, wrong-tag or moved baseline fails closed. Scheduled upstream monitoring still follows new releases and retains all compatibility checks. Use the baseline input for this 2.0.4 feature release; investigate 2.0.5 separately rather than silently expanding its scope. The app bundle and diagnostic-disablement policy are unchanged.

### Redirect fixture timing classification and correction (2026-10-12)

Focused runs exposed `streamfit_redirect_range.c:24` at 575/602 kbps against the unchanged >640 kbps assertion. The paired baseline/candidate audit (38318759984, artifact 11777988431) verified identical hashes for all 15 networking/test inputs. With the same existing loopback HTTPServer-name helper, all six original runs passed; observed relative sleeps requested 2.0 seconds but took 2.64–3.15 seconds. A monotonic-deadline server experiment passed six more runs and restored the nominal 4096-byte/100-ms rate (2.00–2.08 seconds for twenty sleeps). TCP_NODELAY did not remove the measured scheduler drift in the preceding exploratory audit; do not blame or alter production networking.

The maintained test-server adapter now schedules against monotonic deadlines at the original rate. It retains all 200 blocks, real sockets and measurements, headers/redirects, client budgets and original assertions. Reset the pacing deadline after the intentional 2.5-second and 9-second stalls so catch-up never erases stall coverage. The focused gate additionally runs the unchanged diagnostic, parallel-connection and stream-fit fixtures, plus three unchanged redirect repetitions. The first exploratory baseline attempts lacked the custom host helper and failed server startup; they are not throughput evidence. Preserve both failed and passing archives. Do not classify diagnostic experiments as release attestation.

### Published feature baseline on upstream 2.0.4 (2026-10-13)

The feature release is complete. Tizen v2.0.4.68 (run 38319700449) and webOS webos-v2.0.400064 (run 38319762254) published from the same frozen builder f7015cb86e0707ff2fd038e563cd8a18194d8d9f and upstream db6ae4ee0dd2fa158c46ba375c1fe8c08de70504. Each full suite executed 470 required tests with zero failures and zero unverified skips; 107 approved upstream exclusions retain the exact 577-script inventory. Native packages and backend security gates passed. Both final workflows completed on their first attempt, without candidate edits or workflow restarts. Public SOURCE.json and asset checksums were independently verified after publication. See ci-evidence/2026-10-13-release-baseline.json for immutable release evidence.

Sync Now, per-account/profile freshness, Collections/manifest refresh, pending-local edits, MDBList scrobbling/history and prior UI/performance improvements are enabled. Support the Project is removed with saved indices reserved. Private diagnostic collection/pairing/uploads remain disabled; local troubleshooting and crash recovery are preserved. Successful security checks do not override the user's disabled production policy. The preceding 2.0.4.63/2.0.400059 releases remain published rollback options. Tizen's host shell ID matches 2.0.4.63, preserving compatible core-update eligibility; this is not a physical-TV installation test.

Measured final dual-platform elapsed time was 76m11s for Tizen and 60m09s for webOS, exceeding the 30–45-minute target. Tizen's dependency cache missed and the native step rebuilt font/media libraries before compiling the core; the completed cache was saved. The SDK key currently hashes the entire channel.py file, so the unrelated reviewed-release selector invalidated an otherwise unchanged dependency recipe. In a separate CI optimization, isolate dependency-preparation inputs from release-selection code, prove equivalent SDK inputs and preserve integrity checks before reusing cached libraries. Do not alter a running frozen candidate to chase this optimization. Record POSIX CI fingerprints from sealed release evidence: the published value is 26dbeede597d7d6538a4a6aafc6da5edbf1e25779284b3612285bf10f1b46a48; raw Windows working-tree line endings can produce a different local fingerprint.

This published feature baseline is the starting point for the separate upstream 2.0.5 compatibility task. Keep automatic latest-upstream monitoring active. The reviewed-baseline input is an explicit manual feature-release choice, not a permanent pin of scheduled monitoring. Preserve these published assets while adapting 2.0.5 and run focused checks before any new complete release gates.

### Discover and Appearance development checkpoint (2026-10-13)

Start from builder a6bc686 (published core baseline f7015cb) and upstream
2.0.4 db6ae4ee0dd2fa158c46ba375c1fe8c08de70504. The existing published
Tizen 2.0.4.68 and webOS 2.0.400064 remain intact. No upstream upgrade,
monitoring change, diagnostics activation or production release is included.

Discover is a separate native destination; Explore remains unchanged. This
checkpoint browses published addon catalogue snapshots, separates movie and
series types and derives exact genre names from their actual metadata. It
labels loaded-snapshot scope on screen. Available categories depend on the
installed providers and loaded Home rows; provider-wide discovery, remote
filtering/pagination and guaranteed desktop AI/anime/editorial categories
remain unfinished. Artwork uses the existing texture cache, and row/index
work occurs only on filter or catalogue revision changes. Do not describe
this as complete desktop parity or as physical-TV performance validation.

Native cosmetic settings can be local to the device AND scoped to a profile:
keep their existing account-blob exclusion and explicitly include them in
dePerfil. Freeze installation appearance for missing fields in old profile
files, save active preferences on settings commits and apply fonts on restore.
main.c reads settings before loading the saved profile; defer profile restore
until the second settings read, after perfis_carregar_ativo. Restoring during
the early read can checkpoint another profile's values into slot 1. Hardware,
consent, language and accessibility settings remain device-wide. Existing
safe GPU getters continue to preserve preferred values while applying fallback.

Local strict Discover assertions passed, including an empty-carousel OK/Back
regression caught during verification. Changed UI modules compiled with both
NV_TPK and NV_WEBOS definitions on Windows using an isolated time shim; these
are not SDK link/package checks. Both exact-upstream adapter assemblies and
existing Settings/i18n compatibility contracts passed. The builder suite had
69 successes and two Windows checkout byte-integrity errors; all four private
client tests passed after restoring unchanged files to their exact verified
Git bytes. Keep checksum guards intact: this repository contains legacy CRLF
blobs predating its text attributes. Native Appearance runtime assertions are
added to the existing fixture and queued for the focused host gate, not claimed
as passed locally. No full release validation was initiated.

Remaining: complete provider-wide Discover using manifest-declared filters;
implement all four statistics modes with Automatic default and provider-specific
history snapshots/provenance (the current merged watched map is not a sole-
provider source); complete native rendering/profile/restart validation, then
review and freeze a release candidate. Full TV builds and physical-device
checks follow separately. This is a partial development checkpoint.

# Tizen source filtering, season charts and MDBList providers

Ordered patches `tizen-01` through `tizen-05`, `shared-06` and `shared-07` follow
the common `mdblist.patch` on both platforms, before the platform updater.
Every Samsung and LG rebuild applies and tests these improvements. Conflicts stop
the build; the previous published package remains available. `SOURCE.json`
records every improvement patch's SHA-256.

## MDBList account-key sync fix

The fifth patch reads the official client's `features.mdblist_settings.mdblist_api_key`
as a typed value or plain string, including serialized settings responses. It also
decodes both object and serialized-object `credential_json` provider rows, with
the official `credentialJson` alias. Valid provider credentials take priority over
the settings fallback, including an explicit empty value used to remove a key.
Malformed, missing, unsafe and oversized values do not replace a working key.
Credential pulls remain independent of this TV's protected local layout settings.
Existing account/profile-cycle guards still gate application to the active profile.
This fix reads existing account data; it does not upload or bundle personal keys.

Regression tests reproduce the previous serialized-credential failure and cover
typed/serialized profile keys, provider/root isolation, explicit clearing and
rejection of truncated or unsafe values. The key field's Settings status still
shows only presence, never the key itself.

On 9 October the user reported season charts at approximately 25 FPS on their
S95C after updating to 2.0.2.7. This is user-observed improvement, not a controlled
benchmark of every chart or the later account-sync fix.

Official format reference (verified 9 October):
[provider credential service](https://github.com/NuvioMedia/NuvioTVSmart/blob/72473523c18a3fb4bef3a0dba8fb8f91548b3baa/js/core/profile/providerCredentialSyncService.js),
[MDBList settings sync](https://github.com/NuvioMedia/NuvioTVSmart/blob/72473523c18a3fb4bef3a0dba8fb8f91548b3baa/js/core/profile/profileSettingsSyncFeature-mdblist-settings.js).

## Sources

Cached Only defaults ON. The default is saved as `cachedOnlyDefaultLocal` in
the existing preferences mechanism. The sheet's Cached control can immediately
show all sources; the Settings default controls subsequent openings.

Only literal booleans in `streamData.service.cached` establish cache state:
true is Cached, false is Uncached; absent/malformed fields are Unknown.
Strict filtering excludes Unknown. Display names, filenames and lightning
symbols never prove cache availability. Native debrid resolution can mark a
successfully resolved source Cached. Quality, MP4, Dubbed and sorting remain.

AIOStreams receives a compatible User-Agent on its existing stream request.
Its current default server policy supplies structured streamData to such
clients; a server can explicitly disable that feature. Other addons keep
their previous headers. No extra TorBox requests are introduced.

The private exports identify the user's formatter/configuration, but contain
no installed AIOStreams manifest address or live stream response. Actual
instance metadata still requires a TV run. `[source-cache]` diagnostics count
Cached/Uncached/Unknown only, without URLs, hashes, keys or response bodies.
Unknown remains Unknown if the server withholds metadata.

## Season by the Numbers

Show Season by the Numbers defaults ON and persists as
`showSeasonNumbersLocal`. OFF removes the section's layout/focus/rendering
and stops its dedicated requests; shared episode metadata remains available.

Static heatmap, retention and fingerprint chart content is baked into targets
within a shared 6 MiB budget. Data revisions, language/font changes and target
size changes invalidate it; focus overlays remain live. Allocation failure or
nested target rendering falls back to the original direct rendering. Targets
are released when details close or the section is disabled.

With the existing performance meter enabled, `[season-charts]` reports bake
draw calls, texture binds, CPU submission time and allocated bytes. These are
diagnostics, not Samsung GPU-time or FPS measurements. S95C testing is required
for visual parity, navigation, fade effects and any performance claim.

## MDBList Watchlist

Select MDBList Watchlist in Where + Saves. The existing MDBList key is reused;
library selection is independent of playback-scrobbling consent. All saves
are written locally first. Background writes use documented Watchlist
add/remove endpoints and nested `ids` objects, with movie/show distinctions.
Only confirmed result envelopes count as successful. Failed writes surface
a notice and keep local changes. Retry the action after connectivity returns.

Reads follow cursor pagination, deduplicate typed identities and merge with
local saved titles. The compact snapshot has a five-minute TTL, a 2,000-item
limit and a 100-page limit. A loop, limit overflow or failed refresh retains
the previous complete snapshot and reports failure. No arbitrary lists are
written. Authentication failures block until credentials/profile change;
rate limits respect GET Retry-After. POST rate limits back off conservatively.

## MDBList Continue Watching

Select MDBList under Source for Continue Watching. It merges local progress
with paused `/sync/playback` sessions and `/upnext`, using explicit show,
season and episode IDs. Watched history is only a completion veto; it never
creates partial progress. Paused percentages >=80 are excluded, matching the
MDBList scrobble-stop watched boundary. Missing runtimes produce no invented
remaining duration. Local completion thresholds remain unchanged.

Precise local seconds win for the same episode even when older than the
remote timestamp. Approximate remote percentages are not written into local
progress storage. Existing player resume uses the local record when present.
Removal clears the corresponding paused session asynchronously and keeps
the existing local removal marker while the server catches up.

Reads use a five-minute snapshot, at most 128 candidates, 20 Up Next pages
and 20 watched-history pages. History is bounded by the oldest paused instant
when known. Errors/overflow retain the prior snapshot and local progress.
Unknown nested API shapes/episode numbering are omitted rather than guessed.
The API schema leaves several nested response objects unspecified; live
account validation remains necessary. The supplied MDBList key field was
blank, so tests use controlled responses and no live account writes.

API references: [MDBList OpenAPI](https://api.mdblist.com/schema/),
[MDBList docs](https://api.mdblist.com/docs/),
[AIOStreams transformer](https://github.com/Viren070/AIOStreams/blob/b17de1eabd7d98e6f4a65aa01229d215081ff38f/packages/core/src/transformers/stremio.ts),
[AIOStreams stream route](https://github.com/Viren070/AIOStreams/blob/b17de1eabd7d98e6f4a65aa01229d215081ff38f/packages/server/src/routes/stremio/stream.ts).

## Shared tracking, performance and layout correction

Both builders now apply the same seven reviewed patches after the original MDBList
integration. Patch filenames 1–5 are retained to preserve provenance/history.
Settings > Tracking > MDBList provides masked manual API-key entry, connection
validation, account-sync status, independent playback consent, disconnect and a
watched threshold (85% default). Credentials persist per account/profile using
atomic app-private files with owner-only permissions; they are not an encrypted
hardware keychain. Pending edits/removals win over stale cloud pulls until the
existing credential RPC acknowledges them. Unsupported server writes keep the
local key and display an explicit status. OAuth connections are separate from
API keys and cannot be converted into a personal key.

MDBList library requests now use query API-key authentication, matching the
original tracker. Background /user validation and separate HTTP diagnostics
distinguish rejected keys, network failures and quotas. Pause and stop both mark
watched at 80% on MDBList: below the chosen threshold their remote percentage is
capped at 79.99%; exact resume time stays local. Completion is sent once per
playback session; start at the beginning permits an intentional rewatch.
Periodic progress survives as local resume data; unsent in-memory API jobs can
be lost if the process is killed while offline.

A revision/season index removes repeated episode scans, preserving catalogue
order. Collections columns and navigation reserve the fixed detail panel and
focus overhang. Physical-TV frame times, account acceptance and playback remain
pending; controlled regression tests do not establish real-device FPS.
See DEVELOPMENT_LESSONS.md for evidence and regression safeguards.

## Your Progress and Home follow-up

Your Progress is a separate section from Season by the Numbers. Its totals were
already cached, but rebuilding used a linear watched-map lookup per episode.
The new bounded index and consistent batch snapshot reduce repeated history
work; only relevant watched changes invalidate the visible title.

The card preserves readable row sizes through a focus-following season window.
All seasons remain reachable. The original growth animation remains live; settled
graph content is cached within the shared 6 MiB budget. Hidden/closed targets
release without resetting animation gates. Allocation failure renders directly.

Home uses a compact scoped Up Next identifier snapshot instead of copying API
keys and formatting identifiers per card. Native credential persistence and
account sync are unchanged. Existing Tracking settings, independent consent,
85% threshold, Trakt dispatch, retries and completion dedup are preserved.

The Samsung workflow compares actual GLES rendering with published 2.0.2.3 and
2.0.2.11. Synthetic fixtures, Mesa CPU times and submitted draw counts do not
prove restored TV FPS. With the existing meter enabled, tracking stage timings
contain durations/sample counts only. Collections remains a separate preserved
fix from shared patch 6.

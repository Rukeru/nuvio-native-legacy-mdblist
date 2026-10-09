# Tizen source filtering, season charts and MDBList providers

Four ordered patches named `tizen-01` through `tizen-04` follow the common `mdblist.patch` in
the Samsung build. The LG workflow continues applying its existing patches.
Every Tizen rebuild applies and tests all four improvements. Conflicts stop
the build; the previous published package remains available. `SOURCE.json`
records every improvement patch's SHA-256.

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

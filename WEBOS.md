# LG webOS with MDBList tracking

This uses the same tested MDBList playback integration as the Samsung build,
with a separate LG package builder and update channel in this repository.
The first LG cloud build and publication passed. The downloaded IPK was
checked independently against GitHub digests, package metadata and ARM firmware
compatibility. Samsung remains the repository's Latest release.

Install the custom `.ipk` once using your normal LG installation method. Your
personal MDBList key belongs in **Settings → Tracking → MDBList**.
Enable **Track playback with MDBList** for each profile you want to track.
It is off by default.

GitHub checks official upstream releases every six hours, applies the MDBList
patch and LG update patch, tests them, cross-compiles the app with its playback
engine, subtitle renderer and DTS support, and checks the finished package.
It publishes only after GitHub confirms every uploaded checksum. A patch
conflict or failed build leaves the previous release available.

LG releases have `webos-v` tags and filenames ending `_mdblist_arm.ipk`.
They never become GitHub's Latest release, which continues serving Samsung.
The LG app filters the release list and only accepts this repository's exact
LG package naming contract with a SHA-256 digest. Standard and high-cache
packages cannot be silently mixed; this builder produces the standard variant.

With a working Homebrew Channel installation service, the app checks from idle
home and installs the full newer LG package automatically. It does not start
installation during playback, including the mini player. The installation
screen stays open during replacement; the system installer may close the app.
Reopen Nuvio after installation. The Homebrew Channel verifies the IPK checksum.

Without that service, including a normal Developer Mode installation, update
notices and automatic GitHub builds still work. Install new IPKs from your
computer. This build does not root the TV, elevate permissions, bypass Developer
Mode restrictions or renew its session.

LG requires three-part package versions. The custom version is
`major.minor.(upstream_patch * 100000 + workflow_run_number)`, so upstream 2.0.2
on LG workflow run 2 becomes `2.0.200002`. This is still based on upstream 2.0.2.
The version stamp increases on rebuilds and upstream updates. The builder stops
for review if the reserved range is exceeded.

Only the original app's shared service build settings are used from the existing
encrypted `NUVIO_BUILD_PROPERTIES` repository secret. No personal MDBList key,
account token or TV credential is part of the builder or published package.

Corresponding patched source, provenance, component checks and SHA-256 sums
accompany each release. Live MDBList writes, physical LG playback and the
Homebrew installation service have not been tested on a TV here.

References: [LG package versions](https://webostv.developer.lge.com/develop/references/appinfo-json#version),
[Homebrew Channel service](https://github.com/webosbrew/webos-homebrew-channel/blob/main/README.md),
[webOS installation methods](https://www.webosbrew.org/).

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

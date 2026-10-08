# LG webOS with MDBList tracking

This uses the same tested MDBList playback integration as the Samsung build,
with a separate LG package builder and update channel in this repository.
The first LG cloud build and publication passed. The downloaded IPK was
checked independently against GitHub digests, package metadata and ARM firmware
compatibility. Samsung remains the repository's Latest release.

Install the custom `.ipk` once using your normal LG installation method. Your
personal MDBList key belongs in the app's existing account credential settings.
Enable **Settings → Account and profiles → Tracking → Track playback with
MDBList** for each profile you want to track. It is off by default.

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

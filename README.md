# Nuvio Legacy with MDBList â€” Tizen 8 update channel

This companion repository rebuilds **published releases** of
[iqui27/nuvio-native-legacy](https://github.com/iqui27/nuvio-native-legacy),
reapplying MDBList playback tracking before publication. It is intended for
**Rukeru/nuvio-native-legacy-mdblist**. It is an independent custom build.

The prepared files are not a live update service until this repository is uploaded,
its build configuration is installed, and its first Actions run succeeds.

## One-time activation

1. Create the public repository `Rukeru/nuvio-native-legacy-mdblist` and put this
   directory's contents on its default branch, including `.github`.
2. In repository Settings â†’ Secrets and variables â†’ Actions, create the encrypted
   secret `NUVIO_BUILD_PROPERTIES` containing the original app's build properties.
   Do not commit that file. No personal MDBList API key belongs in this secret.
3. Enable Actions, open **Rebuild upstream releases with MDBList**, and select
   **Run workflow**. Resolve any failed checks before expecting updates.
4. Sign the custom unsigned Tizen 8 TPK for your TV and install it once. This is
   necessary to replace the original upstream update destination and install the
   MDBList compatibility guard.
5. Enable MDBList playback tracking in your profile's Tracking settings.

The app service properties preserve Nuvio sign-in, account sync and existing
service integrations. They identify the original app's backend, rather than your
personal login. An empty build is deliberately refused because it would break sign-in.
Supported property names are in upstream `tools/env.sh`: `NUVIO_SUPABASE_URL`,
`NUVIO_SUPABASE_ANON_KEY`, `TV_LOGIN_WEB_BASE_URL`, `TRAKT_CLIENT_ID`,
`TRAKT_CLIENT_SECRET`, `SIMKL_CLIENT_ID`, `SIMKL_APP_NAME`, `TMDB_API_KEY`,
`SEEKR_API_KEY`, `NUVIO_REC_URL`, and `DISCORD_CLIENT_ID`.

## What happens after activation

- GitHub checks for a new published upstream release every six hours. Scheduled
  runs can be delayed by GitHub; this is not an immediate release webhook.
- It applies `mdblist.patch` using Git's three-way merge, runs tracking
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
**Run workflow â†’ force** to rebuild the current release. Failed Actions runs appear
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
bootstrap Tizen 8 host/core compiled successfully. The GitHub Linux build recipe
still needs its first real Actions run; neither live MDBList credentials nor a
physical TV were exercised here.

`SOURCE.json` and the corresponding patched source archive accompany each cloud
release. The official engine's release checksum and exact source commit are recorded.
Third-party source URLs and native build instructions remain in upstream tools.
This repository uses the upstream GPL-3.0 license; third-party notices are retained.

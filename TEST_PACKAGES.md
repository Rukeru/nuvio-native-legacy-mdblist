# Development TV test packages

These packages are for `codex/discover-profile-appearance`, based on upstream
2.0.4. They are not production releases or a frozen candidate. Use only the
`development-test-tizen-<commit>` / `development-test-webos-<commit>` Actions
artifacts. Match `SOURCE.json` to the reviewed commit and verify the package's
SHA-256 against `SHA256SUMS.txt` before installation. Tizen signing changes the
TPK bytes; retain the original verified file and the signed copy separately.

## Preserve data and prepare rollback

1. Keep your currently working full TPK/IPK and Samsung signing certificate.
   Record the installed version. The test packages retain the baseline package
   versions: Tizen 2.0.4; LG 2.0.400064. The Samsung test core identifies itself
   as 2.0.4.9001. LG provenance is the commit in SOURCE.json, not a new version.
2. Run Sync Now in the working app. Confirm completion, then fully close it.
   Note each profile's Appearance settings and statistics preference; native
   Appearance is local to this TV and profile, so cloud sync is not its backup.
3. Use your existing backup method for app data if available. Sync Now is not a
   complete backup of local settings, credentials, caches or pending edits.
   Do not uninstall, clear app data, factory reset, log out, delete profiles or
   change signing identity to get around an installation error.
4. Install as an in-place replacement using the same app identity and, on
   Samsung, the same author certificate. If the installed version is newer or
   the installer requires removal/downgrade, stop. An uninstall can erase data.
   These packages do not execute a data wipe, but installer behavior and rollback
   on your firmware still require physical testing.
5. Keep the working package ready. Roll back by fully closing the test app and
   installing that package in place with the same identity/certificate. If this
   is refused, stop and retain the data; do not uninstall as a workaround.
   A failed-install message is not a successful rollback. Samsung's higher test
   core cannot be rolled back through the normal newer-core updater; use the
   full working TPK. If an existing downloaded core overrides it, stop for
   targeted recovery rather than deleting the whole data directory.

Private diagnostic collection, pairing and uploads remain compiled disabled.
Leave them disabled. Do not use in-app update actions during this test session.
No TV installation is performed by the package workflow.

## Samsung S95C (Tizen 8)

Developer Mode is already enabled and connectivity was confirmed. Keep the PC
and TV on the same LAN. In Tizen Studio Certificate Manager, select the existing
Samsung TV certificate profile; ensure its distributor certificate covers this
TV's DUID. In Device Manager, connect the TV and permit app installation.

Sign the verified unsigned `.tpk` using that profile, then install the signed
TPK with Tizen Studio or its CLI. Example, replacing the profile and filename:

```powershell
sdb connect <S95C-IP>:26101
tizen package -t tpk -s <existing-TV-profile> -o signed -- <unsigned-test.tpk>
sdb -s <S95C-IP>:26101 install <signed-test.tpk>
```

Open Nuvio from the TV launcher after a full process restart. If signing or
replacement fails, preserve the working installation and the exact error.
See [Samsung/Tizen CLI packaging and installation](https://github.com/Samsung/tizen-docs/blob/master/docs/sdk-tools/baseline-sdk/common-tools/command-line-interface.md).

## LG C5 (webOS 26)

Use your existing working Developer Mode or Homebrew installation route. For
Developer Mode, keep its session active, enable Key Server, add the TV in
webOS Dev Manager or `ares-setup-device`, and obtain the key using the displayed
passphrase. Never put that key/passphrase in a bug report. With a paired device
named `c5`, install the verified IPK in place and launch:

```text
ares-install --device c5 <verified-test.ipk>
ares-launch --device c5 space.nuvio.native.legacy
```

With Homebrew access, use the existing installer to install the verified local
IPK in place. Do not change Developer Mode/root status for this test. Native app
installation permissions depend on the existing setup; if the installer refuses
this native package, stop and report the error rather than removing the app.
See [LG CLI installation](https://webostv.developer.lge.com/develop/tools/cli-dev-guide)
and [Developer Mode setup](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app).

## Smoke test on each TV (about 10 minutes)

1. Confirm existing login, profiles, addons and watch history remain present.
   Open Home and Explore, then the separate Discover screen.
2. In Discover choose Movies, Series, two installed-provider catalogues and
   their declared genres. Check hero/logo/cast/metadata, loading/error states,
   row movement, paging, opening details, and returning. Change filters quickly
   and confirm old results do not overwrite the new selection. Use Samsung
   directional/OK/Back controls; on LG also test Magic Remote pointer/wheel.
3. On profile A change font, glass/background or layout. Switch to profile B,
   verify its own values, switch back, fully restart, and verify persistence.
   Device-wide hardware/accessibility settings should keep their shared scope.
4. Under Tracking choose Automatic, Nuvio, MDBList and Trakt statistics in turn.
   Verify each screen names its provider/provenance or partial/unavailable state.
   Nuvio/MDBList must work without Trakt. If a known title exists in two sources,
   Automatic should count its completion identity once. Missing dates/time
   should remain unknown. Restore your preferred mode and switch profiles.
5. Play an existing known-good movie and episode; pause, seek and stop. Check
   Continue Watching/resume and Sync Now. Keep playback-tracking consent as it
   was; use a test title if deliberately exercising watched/scrobble writes.
6. Confirm no private diagnostic upload/pairing UI is enabled. Record TV model,
   firmware, commit, install result and pass/fail for the steps. Share errors or
   screenshots without account tokens, API keys or personal watch-history dumps.

A passing host/GLES build is not physical-TV evidence. Neither platform is
cleared for a release freeze until its installation and smoke test are recorded.

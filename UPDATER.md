# Automatic upstream updates

Both platforms check stable official releases hourly (Samsung at :17, LG at
:47 UTC), and recheck after an integration/updater push. GitHub scheduling can
be delayed; these are polling targets, not guaranteed delivery times. Manual
workflow dispatch and `upstream-release` repository dispatch are also available.

Before a full build, the monitor assembles checksum-verified owned modules and
small, named three-way adapters against the pinned base. The custom Settings
registry and translation keys are independent of upstream array positions.
It checks Settings coverage, language alignment, changed interfaces, C syntax,
tracking, history, unwatch rules, cache and concurrency regressions.

Compatible source proceeds to platform tests and packaging. Publication verifies
the package and every uploaded asset digest while the release is still a draft.
Samsung remains GitHub Latest; LG uses independent `webos-v` package versions.

Transient download/transport failures retry at most three times. Source conflicts
and failing compatibility tests stop immediately, keep the last working release,
and open one issue naming the affected component, files and workflow logs.
The same broken upstream/integration combination is quarantined rather than
rebuilt hourly. A repaired adapter/updater push or a different upstream release
automatically rechecks. The issue closes after successful publication.

For maintainers: edit owned files in `integration/overlay`, adapters in
`integration/*.patch`, or keyed translations in `integration/translations.json`;
update the corresponding SHA-256 in `integration/manifest.json`. Add a regression
for the observed behavior. Keep published historical patches immutable. See
`DEVELOPMENT_LESSONS.md` for preservation requirements and verification limits.

The repository carries these public sources in `integration-bundle.zip` with
its SHA-256. Preflight verifies and safely extracts it before reading the
manifest. After editing the extracted integration, repack it and update the
bundle digest as well as the manifest's individual input digests.

On Samsung, native cores install automatically only when the existing signed
shell, resources and engine match. A new full TPK must be TV-signed and installed
when that identity changes. On LG, automatic package installation requires the
working Homebrew Channel service; Developer Mode needs computer installation.

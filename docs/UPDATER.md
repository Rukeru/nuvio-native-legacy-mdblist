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

The reviewed adapter base is now the immutable upstream 2.0.4 commit. Factory
defaults run through an owned companion that executes the unchanged upstream
test and preserves all original MDBList consent/key/scope/status assertions.
Before publication, both platforms also require the complete upstream host
gatekeeper suite on macOS. Its logs distinguish unavailable tests from passes;
actual platform builds and GLES rendering checks remain separate requirements.

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

The full upstream gatekeeper runs across ten isolated native regression
runners per platform (eight macOS and two Linux). It retains every original test script, assertion,
exclusion and SKIP rule. The aggregate gate rejects missing/failed shards,
duplicate or omitted test scripts, changed inventories and provenance drift.
Both publish jobs require its attestation in addition to the Linux native
build and real rendering checks. Unchanged polls use only the inexpensive
release selector and do not start macOS regression jobs.

On Samsung, native cores install automatically only when the existing signed
shell, resources and engine match. A new full TPK must be TV-signed and installed
when that identity changes. On LG, automatic package installation requires the
working Homebrew Channel service; Developer Mode needs computer installation.
### SDK downloads and publication races

The Tizen SDK adapter validates the upstream ARMv5 Debian base before the full
build and generates a separate Dockerfile using the same immutable manifest
from Google's Docker Hub cache. It does not change the upstream Dockerfile or
raise the target ABI. Docker registry HEAD/GET 429 responses receive bounded
retries; compiler failures in the same log still stop without retrying.

Each new SOURCE.json and release body records the exact builder commit.
Publication compares its workflow tree with the current default branch. If the
workflow changed during the build, the old build stays unpublished and a named
issue explains that a fresh run is needed. This is not quarantined as a source
conflict: the repair push or next hourly poll retries from the current branch.
The tag always targets the tested builder commit; the updater never substitutes
an untested newer commit to bypass GitHub's workflow permission rule. Public API
error messages appear in logs without request bodies or authentication headers.

### Development and release validation

Intermediate pushes run `development.yml`: all updater unit tests, followed by
the conservative `ci_impact.py` map. Integration/bundle/native-builder changes
also run both platforms' maintained adapters, preflight and platform checks;
compiler-wrapper changes run original/cold/warm fixtures on macOS and Linux.
Unknown change categories fail until explicitly classified. These checks never
authorize publication. Use `python3 -m unittest discover -p 'test_*.py'` locally;
native focused checks need the dependencies described in their workflow.

The hourly/manual upstream release workflows retain the complete inventory and
native package gates. Ordinary pushes no longer start full release builds.
Freeze the candidate after focused checks, then dispatch each platform with
force when releasing custom changes against the same upstream version.

`ci-validation.yml` is an explicit nonpublishing infrastructure proof, pinned
to the integration manifest's upstream commit. Its `diagnostic_only` evidence
is rejected by the publication validator. It runs the complete inventory but
does not manufacture a new TV package or call an old package a new build.

Compiler caching stores only verified object work, never test results. Unknown
compiler forms pass unchanged to the real compiler; timed test workloads are
not parallelized within a runner. The full benchmark retains every frame and
scenario on its own Linux runner. Platform results remain separate because
their integration fingerprints/configuration differ; equivalence has not been
established for sharing test results.

Shard, selection, native package and aggregate artifacts include run attempt.
Retry only confirmed transient failures on the same commit. The aggregate
retains all archives, selects the latest attempt, checks source/compiler/image/
dependency identity, and rejects failed, incomplete or unverified results.
Successful earlier jobs retain their named output artifacts; never delete
evidence to resolve a retry upload collision.

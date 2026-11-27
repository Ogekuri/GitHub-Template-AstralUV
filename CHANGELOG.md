# Changelog

## [0.0.10](https://github.com/Ogekuri/GitHub-Template-AstralUV/releases/tag/v0.0.10) - 2026-11-27
### ⛰️  Features
- add TODO and line-wrap mandates, unwrap README paragraphs [useReq] *(README)*
  Add mandatory SRS requirements DES-070..DES-073 for README.md: every top-level chapter MUST begin with a TODO completion note, and prose MUST NOT be hard-wrapped across source lines. Unwrap all README.md paragraph, list-item, blockquote, and inline-HTML continuations onto single lines, preserving every TODO note, table row, command argv, code fence, and HTML badge element unchanged.
- Add .galias.conf file.
- add one-shot template rename script with sandbox pytest [useReq] *(rename-me)*
  Add scripts/rename-me.sh (PRJ-010): parameter validation (DES-062/063),
  ordered string substitutions (DES-064/065), deepest-first path renames
  (DES-066), publish-action publishname pre-pass (DES-067), residual
  verification and self-removal on success (DES-068/069).
  Add tests/test_rename_me.py (TST-033/034): complete seven-parameter
  rename over a temp/ sandbox copy, optional-parameter preservation,
  missing-parameter failure before any mutation.
  Extend the SRS with the rename-instantiation mapping, A-14/A-15, the
  CTN-014 maintenance mandate, and the PROC:rename-tooling runtime unit.
- Add disable-version-check config switch for the online check [useReq] *(version-check)*
  REQUIREMENTS.md: add REQ-042..REQ-045 defining the
  version_check:disable-version-check Selection parameter (default no),
  startup-check suppression (REQ-043), tolerant missing/invalid
  configuration handling (REQ-044), and the always-active --ver /
  --version report (REQ-045); adapt REQ-007, TST-008, TST-010; add
  TST-025, TST-026.
  config.py: add the version_check schema section and the tolerant
  runtime reader version_check_disabled().
  core.py: skip the gated pre-dispatch PyPI check only when the switch
  is enabled; --ver/--version remain active.
  config_render.py: make the --info Meaning column schema-generic for
  non-palette enum tokens (DES-010).
  tests: new switch-suppression, tolerance, report-always-active, and
  config CLI round-trip cases; golden trees updated to the schema shape
  (49 passed, ruff clean).

### 🏗️  Implementations
- implement CLI app, version check, tests, and runtime docs [useReq] *(core)*
  Implement the SRS end-to-end from the extracted skeleton:
  Initialize repo: skell.tgz extraction, keyword substitution,
  scripts/src renames (CTN-001..004).
  Add githubtemplateastraluv package: core dispatch, management
  commands, idle-time cached version check (REQ-001..015).
  Packaging: console entry points, frozen-lock consistency, gitignore
  usereq/ tracking (DES-001..003).
  Tests: HDT suite covering TST-001..TST-007; WORKFLOW.md runtime
  model and REFERENCES.md refreshed.

### 🐛  Bug Fixes
- derive TST-016 dist artifact names from declared version [useReq] *(tests)*
  TST-016 (DES-021..DES-025, DES-052) asserted hardcoded 0.0.6 wheel/sdist names and failed after the 0.0.7 release bump (1 failed / 66 passed in the pre-release gate).
  Derive the expected dist/ artifact pair from the sandbox pyproject.toml project.version via the module tomllib pattern, matching the test's declared-version contract. Test-only change; requirements unchanged.
  Verified: uv run pytest -q -> 67 passed; scripts/pre-release-check.sh -> all pre-release checks passed; repository left clean.
- rebuild stale 0.0.4 release artifacts to 0.0.5 [useReq] *(dist)*
  pyproject.toml declared version 0.0.5 while the git-tracked dist/ artifacts still embedded Version 0.0.4; a 0.0.5 tag would have published the stale pair verbatim via OIDC trusted publishing (DES-017, DES-042). Regenerated the sdist and wheel via scripts/build.sh (clean startup state, stale prune, frozen build). Full pytest suite passes (45 passed); pre-release check exits 0 with a clean tree.
- Update version number. *(config)*
- rebuild 0.0.4 release artifacts and align uv.lock [useReq] *(dist)*
  The v0.0.3 and v0.0.4 tags carried the stale 0.0.2 dist/ pair, so the
  release workflow published a duplicate 0.0.2 that PyPI rejected and the
  PyPI row of --ver stayed 0.0.2 while GitHub reached 0.0.4. Rebuilt the
  dist/ pair from the 0.0.4 tree via scripts/build.sh (DES-042, DES-023)
  and aligned uv.lock to 0.0.4; suite 45 passed incl. the dist-metadata
  contract test; pre-release-check passed with clean repository.
- Update uv.lock file.
- tolerate stale-schema files in --print/--info rendering [useReq] *(config)*
  A configuration file persisted by the pre-55fd527 schema (Notifications
  section) aborted --print and --info with a sections-mismatch error
  instead of printing the mandated schema-empty tree (TST-008, DES-010).
  New config.load_display projects the persisted payload onto the schema:
  unknown keys are dropped and known missing keys fall back to schema
  defaults; --print and --info load through it. load_strict and
  --get/--set/--unset/--print-raw keep strict validation (REQ-023);
  malformed JSON and non-object roots still fail with exit 1.
  HDT stale-schema reproducer added; uv run pytest: 45 passed;
  req-static-check clean; WORKFLOW.md and REFERENCES.md updated.
- Update uv.lock file.
- rebuild release artifacts with valid PyPI classifier [useReq] *(dist)*
  dist/ still held the stale v0.0.0 artifacts embedding the PyPI-rejected
  'Topic :: Software Development :: Configuration Management' classifier;
  the release workflow publishes dist/ verbatim at the tag commit
  (DES-042) and would repeat the 400 Bad Request (DES-016, DES-017).
  Rebuild dist/ via scripts/build.sh into v0.0.2 artifacts carrying the
  valid 'Topic :: Utilities' metadata. Add the HDT contract test
  test_dist_artifacts_metadata_match_pyproject_and_pypi_acceptance
  (embedded Version/Classifier equal to pyproject.toml, rejected
  classifier absent) and fix a pre-existing no-op assert in TST-013.
  Tests: uv run --frozen pytest -> 44 passed; static check clean.
- replace invalid PyPI topic classifier [useReq] *(pyproject)*
  PyPI rejected the distribution upload with 400 Bad Request: 'Topic :: Software Development :: Configuration Management' is not a valid classifier. Replace it with the valid 'Topic :: Utilities' classifier so OIDC trusted publishing (DES-016, DES-017) succeeds.
  Add the HDT contract test test_pyproject_classifiers_are_pypi_accepted asserting every project.classifiers entry stays PyPI-valid, and derive the help/report version oracles from the single version source core.__version__ (restores TST-001/TST-002 after the 0.0.1 version bump).
  Tests: uv run --frozen pytest -> 43 passed, 0 failed.
- Fix clean.sh script.

### 🚜  Changes
- BREAKING CHANGE: persist only non-default delta configuration entries [useReq] *(config)*
  REQUIREMENTS: add REQ-049..REQ-052, DES-074, TST-035..TST-036; refine
  REQ-017, REQ-018, DES-010 toward delta-only persistence.
  config: subset schema validation, prune_defaults, empty-object
  bootstrap, default-aware get_value, pruning set/unset mutations.
  tests: cover delta-only persistence, default resolution of absent
  entries, and empty-object bootstrap (TST-035, TST-036).
  README: document the delta-only configuration file content.
- deploy templateastraluv short-name executable alongside long name [useReq] *(packaging)*
  DES-003 now mandates exactly two console-script entry points: githubtemplateastraluv (long name) and templateastraluv (short name), both bound to githubtemplateastraluv.__main__:main so uv tool install deploys the identical CLI dispatch under both names (REQ-048, A-11). TST-031 updated to the dual entry-point contract; test_pyproject_declares_dual_entry_points replaces the single-entry-point assertion. Full suite green: 67 passed.
- install --upgrade --develop from GitHub develop branch [useReq] *(management)*
  REQ-032/REQ-036 now mandate the develop branch head via git+...AstralUV.git@develop. UPGRADE_DEVELOP_COMMAND and UPGRADE_DEVELOP_FORCE_COMMAND updated accordingly; README command rows and version-report docstrings aligned (DES-019, DES-059); exact-argv test assertions updated (TST-003, TST-014, TST-032).
- harden version check, docs, packaging and template tooling [useReq] *(core)*
  Requirements: add REQ-046/047, CTN-012/013, DES-057..060, TST-027..032; fix DES-002 workflow name, DES-003 single entry point, DES-009 layout, CTN-002 substitution list (drop .g.conf).; Source: best-effort cache writes (REQ-046), tolerant version parsing (REQ-047), public config.section API (DES-058), launcher uv guard and --frozen delegation, setuptools>=77 floor, single console script.; Docs: README command tables and configuration section corrected; WORKFLOW.md and REFERENCES.md regenerated.; Tests: cover TST-009, TST-011, TST-016..TST-020, TST-024, TST-027..032 (64 passed).
- Update .galias.conf file. *(config)*
- Upgrade uv.lock file. *(config)*
- BREAKING CHANGE: upgrade installed tool via uv tool upgrade [useReq] *(cli)*
  REQ-003: non-forced --upgrade runs 'uv tool upgrade
  githubtemplateastraluv', replacing an already-installed tool.
  REQ-032: develop variant runs 'uv tool install --reinstall --from
  git+...' because 'uv tool upgrade' rejects --from.
  REQ-037 relaxed: forcing triple stays exclusive to --force variants.; REQ-034 unchanged: --dev alias stays removed.; Tests pin the literal REQ-003/REQ-032 argv strings (TST-003/TST-014).
- BREAKING CHANGE: remove configurable notification colors, embed hardcoded color JSON [useReq] *(config)*
  REQ-024/REQ-025 removed: the Notifications section leaves the configuration schema and every canonical path is now rejected (REQ-022). REQ-026 rewritten; REQ-040/REQ-041 added: all colors live in the embedded internal JSON COLOR_CONFIG_JSON of the new src/githubtemplateastraluv/colors.py (bright_green/bright_red assignments plus the 7-token ANSI palette). version_check now consumes colors.notification_colors; config.load_tolerant and config.notification_colors are removed. TST-008, TST-010, TST-011 updated for the schema-empty configuration; README rewritten accordingly. Verification: uv run pytest -> 44 passed; req-static-check clean; schema-empty CLI smoke test (print/get/print-raw) verified.
- document all implemented commands in inline help and docs [useReq] *(help)*
  REQ-001 help template now lists a Configuration Commands section with --get, --set, --unset, --print, --info, --print-raw and fixes the --help entry; the Commands: ... placeholder is removed (A-02). New REQ-039 mandates exhaustive command enumeration in --help; TST-001 verifies REQ-001 and REQ-039 through the byte-exact help oracle. README command reference plus generated REFERENCES.md and WORKFLOW.md updated. Verification: uv run pytest -> 44 passed; req-static-check clean.
- render config tables with rounded borders and double header separator [useReq] *(config-render)*
  Requirements: add DES-053..DES-056 mandating the --print/--info table glyph palette (dash, pipe, rounded corners, single-line junctions, double-line header separator) and TST-024 verification procedure.; Source: format_table/border in config_render.py now emit rounded corners, the double-line header/content separator, and single-line separators between consecutive content rows with identical measured column boundaries.; Docs: WORKFLOW.md call-trace role text updated; REFERENCES.md regenerated.; Tests: existing pytest suite (42 tests) passes; no golden-glyph tests existed.
- prune all stale dist formats, make dist artifacts non-mandatory [useReq] *(build)*
  DES-023: stale-artifact cleanup in scripts/build.sh now covers
  *.tar.gz, *.tgz, *.whl, *.zip at any version; non-artifact files
  preserved (verified with stale v0.0.1/v8.8.8/v9.9.9 seeds).
  DES-025: dropped the mandate to leave artifacts in dist/; the
  final artifact summary is retained.
  DES-039 removed; DES-017, DES-042, TST-019, TST-021 no longer
  impose committed dist/ artifacts (present but not mandatory).
  Committed dist/ sdist and wheel as optional release artifacts.; Verified: req-static-check clean; uv run pytest 42 passed;
  scripts/build.sh executed twice, exit 0, no stale accumulation.
- BREAKING CHANGE: add --force upgrade, --ver failure reason, track dist/ [useReq] *(cli)*
  REQ-001: help screen gains the Options section (--develop, --force).; REQ-003/REQ-032: standard upgrade executes without forcing options.; REQ-035..REQ-038: --upgrade [--develop] --force forces full
  re-download and reinstallation (uv --force --reinstall --refresh).
  REQ-030: failed --ver sources render unknown (<reason>).; DES-039: dist/ artifacts tracked via .gitignore !dist/**/*.; DES-017/018/042/043: release workflow publishes the committed dist/
  artifacts and never builds or runs release-preparation checks.
  Tests updated (38 passed); requirements, workflow model and
  references refreshed.
- BREAKING CHANGE: remove legacy --dev upgrade alias [useReq] *(cli)*
  Drop the --dev alias of --develop from the --upgrade dispatch;
  --upgrade --develop remains the sole develop source modifier
  (REQ-032 and REQ-034 updated in the SRS scope and Functions).
  Remove the unit test implementing the removed legacy alias.; Update README usage section; regenerate WORKFLOW and REFERENCES.; Help screen unchanged and validated against the REQ-001 template.; Verification: req-static-check clean; uv run pytest 32 passed / 0 failed.
- pin workflow runners to ubuntu-24.04 [useReq] *(release-pypi)*
  Pin all three release-pypi.yml job runners to the explicit ubuntu-24.04 label (DES-041), mitigating the GitHub ubuntu-latest rolling migration to Ubuntu 26.04 (2026-10-19..2026-11-19).; SRS: add A-13 (mitigation assumption), DES-041 (runner pin mandate), TST-020 (verification procedure).
- add release build and pre-release check tooling [useReq] *(scripts)*
  scripts/build.sh: toolchain validation, stale dist prune, native uv build
  into dist/ with artifact verification and summary (PRJ-007, DES-020..025).
  scripts/pre-release-check.sh: fail-fast checks (bash -n, compileall,
  pytest, out-of-tree build, artifact validation) with trap-based
  baseline-diff cleanup and integrity verification (PRJ-008, DES-026..038,
  CTN-011).
  .gitignore: targeted dist artifact rules plus !dist/ traversal, inverse
  exclude-then-include strategy preserved (DES-039, DES-040).
  SRS: add PRJ-007/008, CTN-011, DES-020..040, TST-016..019; WORKFLOW.md
  gains four execution units and five communication edges.
- publish to PyPI via OIDC on master, PyPI-first upgrade and version report [useReq] *(release-pypi)*
  Rename release workflow to release-pypi.yml; build and GitHub release run
  for every canonical tag, new OIDC Trusted Publishing job
  (pypa/gh-action-pypi-publish, id-token: write) executes only for master
  tags (DES-016..DES-018).
  Automatic version check now queries the PyPI JSON API (REQ-009);
  --ver/--version print the aligned Current Installed / Latest @ PyPI /
  Latest @ GitHub report (REQ-002, REQ-027..REQ-031).
  --upgrade installs from PyPI (REQ-003); new --develop/--dev modifier
  installs the latest GitHub tagged release (REQ-032..REQ-034).
  README documents PyPI primary install, uvx alternative, and a dedicated
  GitHub section (DES-019); requirements and HDT tests updated
  (TST-013..TST-015).
- migrate release actions to Node24 runtimes [useReq] *(release-uvx)*
  Bump release-uvx.yml JavaScript actions to Node24-or-later majors:
  checkout v4->v5, setup-python v5->v7, attest-build-provenance v1->v4,
  action-gh-release v2->v3. Composite setup-uv and changelog builder v6
  (node24 since v6.0.0) stay unchanged. Add DES-015 pin mandate and
  CTN-010 fallback-variable prohibition to the SRS; add TST-012
  pin-compliance unit tests (suite: 23 passed).
- add additive configuration CLI with deterministic tree renderer [useReq] *(config)*
  Add config.py (canonical Notifications schema, strict validation, atomic JSON persistence, canonical path resolution, --get/--set/--unset/--print-raw handlers) and config_render.py (shared data-driven box-drawing renderer and measured-width table formatter for --print/--info). Extend core.py dispatch additively; version_check.py now renders notifications with configured colors falling back to schema defaults (REQ-024..026). Requirements: PRJ-006, DES-010..014, REQ-016..026, TST-008..011; existing TST-001..007 interfaces preserved (14/14 pass).

### 📚  Documentation
- Update README.md file.


# History

- \[0.0.10\]: https://github.com/Ogekuri/GitHub-Template-AstralUV/releases/tag/v0.0.10

[0.0.10]: https://github.com/Ogekuri/GitHub-Template-AstralUV/releases/tag/v0.0.10

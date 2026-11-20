# Changelog

## [0.0.4](https://github.com/Ogekuri/GitHub-Template-AstralUV/releases/tag/v0.0.4) - 2026-11-20
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


# History

- \[0.0.4\]: https://github.com/Ogekuri/GitHub-Template-AstralUV/releases/tag/v0.0.4

[0.0.4]: https://github.com/Ogekuri/GitHub-Template-AstralUV/releases/tag/v0.0.4

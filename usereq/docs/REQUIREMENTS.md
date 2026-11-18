# githubtemplateastraluv Requirements

## 1. Introduction

### 1.1 Document Rules
This document MUST follow these authoring rules (LLM-first, normative SRS):
- This document MUST be written and maintained in English.
- Use RFC 2119 keywords exclusively (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY). Do not use "shall".
- In requirements sections, every bullet MUST be a requirement and MUST start with a unique, stable Requirement ID (e.g., **REQ-001**).
- Requirement IDs MUST be stable: never renumber, reuse, or repurpose an ID. Only the dedicated reorganization workflow may renumber and it MUST emit an old→new ID mapping.
- Requirement ID prefixes MUST be consistent; the prefixes PRJ (project functions), CTN (project constraints), DES (design/implementation mandates), REQ (functional behaviors), and TST (verification requirements) are defined here before first use.
- Each requirement MUST be atomic, single-sentence, and testable; target <= 35 words per requirement; split any compound behavior into separate IDs.
- Write for other LLM Agents and automated parsers (high semantic density; no filler).
- On every change to this document:
  - Keep the first line as a level-1 title beginning with `# `.
  - Do NOT add YAML front matter or in-document revision history; use git history / CHANGELOG.md for change tracking.

### 1.2 Project Scope
Project `githubtemplateastraluv`: a Python CLI application published on PyPI (`https://pypi.org/project/githubtemplateastraluv/`) and distributed as an Astral UV tool via `uv tool install githubtemplateastraluv` or executed on-the-fly via `uvx`; `git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` remains the optional development source of the `--upgrade --develop` variant; the repository doubles as the GitHub template `Ogekuri/GitHub-Template-AstralUV` ("GitHub template for Astral-UV app", author Francesco Rolando).

Interface: text-only CLI in English; no GUI functionality is requested. Functional areas: management commands (`--help`, `--ver`, `--version`, `--upgrade`, `--uninstall`, with the `--develop`/`--dev` source modifier of `--upgrade`) independent from core logic; automatic online new-version check against PyPI throttled by an idle-time JSON cache; `--ver` dual-source report covering PyPI and GitHub; colored console notifications. Configurability: version-check parameters (endpoint, timeout, and idle-delays) remain hardcoded constants and stay unexposed (CTN-008); the cache location derives from the `$HOME` environment variable; notification colors are user-configurable through a JSON configuration CLI (`--get`, `--set`, `--unset`, `--print`, `--info`, `--print-raw`) persisting state at `$HOME/.config/githubtemplateastraluv/config.json` (REQ-024). No application project-local configuration layer exists; the repository-root `.g.conf` file belongs to repository tooling and is not application configuration. Performance constraints: HTTPS timeout of 2 seconds; cache gating avoids redundant network calls.

Component model: the CLI entry `src/githubtemplateastraluv/__main__.py` dispatches to management commands and core logic; a dedicated version-check component performs the HTTPS queries (PyPI JSON API for the gated check and the report, GitHub releases API for the report), cache persistence, and notification rendering before argument parsing; `scripts/templateastraluv.sh` wraps local execution.

Keyword substitution mapping (skeleton initialization):

| Keyword | Resolved value |
| --- | --- |
| `%AUTHOR%` | Francesco Rolando |
| `%DESCRIPTION%` | GitHub template for Astral-UV app |
| `%PROGRAM%` | githubtemplateastraluv |
| `%SHORTNAME%` | templateastraluv |
| `%SRCDIR%` | githubtemplateastraluv |
| `%OWNER%` | Ogekuri |
| `%REPOSITORY%` | GitHub-Template-AstralUV |

Assumptions (non-normative; reversible interpretations of unspecified details):
- **A-01**: The literal `(x.y.z)` in the help usage line is a runtime placeholder for the current installed version; all remaining help text is printed verbatim.
- **A-02**: The `Commands:` section of the help screen ends with the literal `...` line because no application commands are specified.
- **A-03**: Cache JSON key names are unspecified; the implementation MUST choose stable descriptive keys (e.g., `last_check_epoch`, `last_check_human`, `idle_time_epoch`, `idle_time_human`) and use them consistently.
- **A-04**: A successful check with no newer release prints no notification and refreshes the cache with the standard 3600-second idle-delay.
- **A-05**: On a failed check, the cache last-check timestamp records the failed attempt time and idle-time equals attempt time plus 86400 seconds.
- **A-06**: After the automatic version check, execution always continues with normal argument parsing, regardless of the check outcome.
- **A-07**: Version-check messages use English wording, preserving the user-request semantics "version available" versus "installed version".
- **A-08**: The HTTPS client uses the Python standard library; no third-party HTTP library is mandated.
- **A-09**: "Linux" detection MAY use `sys.platform == "linux"` or equivalent; all other platforms take the manual-command branch.
- **A-10**: No unit tests were explicitly requested; Section 4 defines verification procedures for downstream development.
- **A-11**: The console-script entry point name equals `%PROGRAM%` (`githubtemplateastraluv`).
- **A-12**: The renamed skeleton copy (`src/templateastraluv/`) and the distributed application sources (`src/githubtemplateastraluv/`) coexist as prescribed by the user request.

## 2. Project Requirements

### 2.1 Project Functions
- **PRJ-001**: MUST provide the Python CLI application `githubtemplateastraluv`, published on PyPI, installable as an Astral UV tool via `uv` and executable on-the-fly via `uvx`.
- **PRJ-002**: MUST support local execution of the CLI through the launcher script `scripts/templateastraluv.sh`.
- **PRJ-003**: MUST provide text-based management commands `--help`, `--ver`, `--version`, `--upgrade`, and `--uninstall`, implemented independently from the core application logic.
- **PRJ-004**: MUST provide an automatic online new-version check that runs before CLI argument parsing and is throttled by an idle-time cache.
- **PRJ-005**: MUST provide a text-only CLI interface in English; no GUI functionality is required.
- **PRJ-006**: MUST provide configuration CLI commands `--get`, `--set`, `--unset`, `--print`, `--info`, and `--print-raw`, implemented additively without altering existing commands.
- **PRJ-007**: MUST provide `scripts/build.sh`, an executable Bash script generating the complete distribution package with the project's native build tooling into `dist/`.
- **PRJ-008**: MUST provide `scripts/pre-release-check.sh`, an executable Bash script performing the full release-readiness verification and leaving no generated artifacts in the repository.

### 2.2 Project Constraints
- **CTN-001**: MUST initialize the repository by extracting `../skell.tgz` into the working directory, overwriting existing files and preserving empty directories.
- **CTN-002**: MUST replace all seven keywords mapped in Section 1.2 with their resolved values in: `.g.conf`, `README.md`, `pyproject.toml`, `uv.lock`, `src/skell/core.py`, `scripts/skell.sh`, `src/skell/__main__.py`.
- **CTN-003**: MUST rename `scripts/skell.sh` to `scripts/templateastraluv.sh` after keyword substitution.
- **CTN-004**: MUST rename the `src/skell` directory to `src/templateastraluv` after keyword substitution.
- **CTN-005**: MUST generate application source files under `src/githubtemplateastraluv` following the pre-imposed skeleton schema.
- **CTN-006**: MUST hardcode the version-check HTTPS timeout to 2 seconds.
- **CTN-007**: MUST hardcode the standard idle-delay to 3600 seconds and the failure backoff idle-delay to 86400 seconds.
- **CTN-008**: MUST NOT expose configuration surfaces (CLI options or files) altering endpoint, timeout, or idle-delay values; the cache directory MUST derive from `$HOME`.
- **CTN-009**: MUST execute `--upgrade` and `--uninstall` side effects only on Linux, delegating to the installed `uv` command-line tool.
- **CTN-010**: MUST NOT set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` or `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` in `.github/workflows/release-pypi.yml`.
- **CTN-011**: MUST NOT execute destructive git commands (`git clean -fdx`, `git reset --hard`) inside `scripts/build.sh` or `scripts/pre-release-check.sh`.

## 3. Requirements

### 3.1 Design and Implementation
- **DES-001**: MUST implement the application in Python with `pyproject.toml` packaging metadata compatible with `uv build`, `uv tool install`, and `uvx`.
- **DES-002**: MUST declare in `pyproject.toml` every package, module, and data file required for `.github/workflows/release-uvx.yml` to build a complete distributable package.
- **DES-003**: MUST expose a console-script entry point named `githubtemplateastraluv` that invokes the CLI defined in `src/githubtemplateastraluv/__main__.py`.
- **DES-004**: MUST place application sources under `src/githubtemplateastraluv/` with the CLI entry in `__main__.py` and core logic in `core.py`, mirroring the skeleton layout.
- **DES-005**: MUST isolate management commands (`--help`, `--ver`, `--version`, `--upgrade`, `--uninstall`) from core logic in a dedicated module or clearly separated functions.
- **DES-006**: MUST isolate the online version check (HTTPS query, cache persistence, notification rendering) in a dedicated component invoked before argument parsing.
- **DES-007**: MUST store the cache file at `$HOME/.cache/githubtemplateastraluv/check_version_idle-time.json`, creating missing parent directories.
- **DES-008**: SHOULD render notifications with ANSI SGR colors: bright green for availability, bright red for errors.
- **DES-009**: SHOULD follow the proposed repository layout below (depth-limited; generated and virtual directories omitted).

```
.
├── .g.conf
├── .github/
│   └── workflows/
│       └── release-pypi.yml
├── README.md
├── pyproject.toml
├── uv.lock
├── scripts/
│   └── templateastraluv.sh
├── src/
│   ├── githubtemplateastraluv/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── config.py
│   │   ├── config_render.py
│   │   ├── core.py
│   │   ├── management.py
│   │   └── version_check.py
│   └── templateastraluv/
│       ├── __main__.py
│       └── core.py
├── tests/
│   └── test_githubtemplateastraluv.py
└── usereq/
    └── docs/
        └── REQUIREMENTS.md
```

- **DES-010**: MUST define one canonical in-code configuration schema covering sections, parameters, types, constraints, defaults, and descriptions, driving validation, path resolution, display, and documentation output.
- **DES-011**: MUST isolate the configuration subsystem (schema, validation, atomic persistence, CLI handlers, renderer) in dedicated modules under `src/githubtemplateastraluv/`.
- **DES-012**: MUST render `--print` and `--info` through one shared data-driven renderer emitting UTF-8 box-drawing trees from typed configuration nodes.
- **DES-013**: MUST produce every table through one measured-width formatter rendering rectangular box-drawing rows anchored to the owning parameter detail prefix.
- **DES-014**: MUST persist `--set` and `--unset` updates atomically via a same-directory temporary file, fsync, atomic replace, and prior-file preservation on any failure.
- **DES-015**: MUST pin every JavaScript action referenced by `.github/workflows/release-pypi.yml` to a major version whose declared runtime is Node24 or later.
- **DES-016**: MUST name the release workflow file `release-pypi.yml`, matching the pending PyPI trusted publisher (project `githubtemplateastraluv`, repository `Ogekuri/GitHub-Template-AstralUV`, workflow `release-pypi.yml`).
- **DES-017**: MUST publish built distributions to PyPI via OIDC Trusted Publishing through `pypa/gh-action-pypi-publish` granted `id-token: write`, only when the triggered tag belongs to `master`.
- **DES-018**: MUST execute the build and GitHub release jobs for every canonical version tag on any branch, gating only the PyPI publish job on the `master` branch check.
- **DES-019**: MUST keep `README.md` documenting PyPI installation as the primary method, an Astral uv/uvx alternative-installation section, and a dedicated non-primary section for installation from GitHub with the `--develop` upgrade.
- **DES-020**: MUST implement `scripts/build.sh` in Bash, resolving the repository root independently of the invocation directory and handling paths containing spaces.
- **DES-021**: MUST validate required build tooling (`git`, `uv`) before building and terminate non-zero when any required tool is missing.
- **DES-022**: MUST build distributions by executing `uv run --frozen --with build python -m build` from the repository root, matching the release workflow build step.
- **DES-023**: MUST remove from `dist/` only previously generated artifacts matching `*.tar.gz` and `*.whl` before building, preserving every other file.
- **DES-024**: MUST terminate non-zero with a diagnostic when the build fails or when `dist/` lacks at least one sdist and one wheel.
- **DES-025**: MUST leave the generated release artifacts in `dist/` and print a final summary listing every produced artifact.
- **DES-026**: MUST implement `scripts/pre-release-check.sh` in Bash, resolving the repository root independently of the invocation directory and handling paths containing spaces.
- **DES-027**: MUST execute checks fail-fast, terminating non-zero on the first failed mandatory check with a diagnostic naming the failed check.
- **DES-028**: MUST validate the mandatory toolchain (`git`, `uv`) and treat any missing tool as a failed check.
- **DES-029**: MUST validate tracked shell scripts with `bash -n` and run ShellCheck on them when ShellCheck is installed.
- **DES-030**: MUST compile all tracked Python sources and test files with the project interpreter and treat any compilation error as a failed check.
- **DES-031**: MUST execute the complete pytest suite via `uv run pytest` and treat any test failure as a failed check.
- **DES-032**: MUST perform the complete build into a temporary output directory outside the repository, generating no build artifacts inside the repository tree.
- **DES-033**: MUST verify the built release artifacts exist and are structurally valid (readable sdist tarball and wheel archive) and treat any invalid artifact as a failed check.
- **DES-034**: MUST remove, on success and on failure, every artifact, cache, and temporary file generated by the execution, using trap-based exit and signal handling.
- **DES-035**: MUST terminate non-zero when final cleanup fails, even when all checks passed, and MUST NOT mask the original check outcome.
- **DES-036**: MUST restrict cleanup to paths generated by the execution and MUST NOT delete user files, tracked content, or pre-existing modifications.
- **DES-037**: MUST verify repository integrity at completion by comparing `git status --porcelain --ignored` output with the pre-execution baseline.
- **DES-038**: MUST print readable per-phase logs and a final summary reporting the overall outcome and the failed phase on any failure.
- **DES-039**: MUST ignore generated distribution artifacts through specific `.gitignore` rules matching `dist/*.tar.gz`, `dist/*.whl`, and `dist/*.zip` instead of the blanket `dist/` exclusion.
- **DES-040**: MUST preserve the `.gitignore` inverse exclude-then-include strategy and make `dist/` traversable so versionable files under it can be selectively re-included.

### 3.2 Functions
- **REQ-001**: MUST print the verbatim English help screen (template below) when invoked with `--help` or with no arguments.

```
Usage: githubtemplateastraluv [command] [options] (x.y.z)

Management Commands:
  --upgrade   - Reinstall githubtemplateastraluv on Linux; print manual command elsewhere.
  --uninstall - Uninstall githubtemplateastraluv on Linux; print manual command elsewhere.
  --ver       - Print the githubtemplateastraluv version.
  --version   - Print the githubtemplateastraluv version.
  --help      - Print the full help screen or the help text of a specific command.

Commands:
  ...
```

- **REQ-002**: MUST print for `--ver` and `--version` the three-row version report with aligned version columns, bypassing the idle-time gate and cache file.
- **REQ-003**: MUST execute `uv tool install githubtemplateastraluv --force` when `--upgrade` runs on Linux, resolving the package from PyPI.
- **REQ-004**: MUST NOT execute any upgrade command on non-Linux operating systems; MUST print a warning and the manual command of REQ-003 instead.
- **REQ-005**: MUST execute `uv tool uninstall githubtemplateastraluv` when `--uninstall` runs on Linux.
- **REQ-006**: MUST NOT execute any uninstall command on non-Linux operating systems; MUST print a warning and the manual command of REQ-005 instead.
- **REQ-007**: MUST run the automatic version check before argument parsing on every invocation, subject to REQ-008 gating; `--ver` and `--version` bypass the gate.
- **REQ-008**: MUST perform the HTTPS request only when the cache file is absent or the current epoch is greater than or equal to the cached idle-time; otherwise skip the check.
- **REQ-009**: MUST query `https://pypi.org/pypi/githubtemplateastraluv/json` with a 2-second timeout whenever the check executes.
- **REQ-010**: MUST persist, after every executed check, a cache JSON containing four fields: last-check epoch, last-check human-readable, idle-time epoch, idle-time human-readable.
- **REQ-011**: MUST compute the idle-time epoch as the last-check epoch plus the applicable idle-delay: 3600 seconds on success, 86400 seconds on failure.
- **REQ-012**: MUST print a bright green message comparing the available PyPI version with the installed version when a newer PyPI version is found.
- **REQ-013**: MUST refresh the cache with the standard 3600-second idle-delay after every successful HTTPS check, regardless of comparison outcome (A-04).
- **REQ-014**: MUST print a bright red message reporting the encountered error for any failed HTTPS check (HTTP 429, 503, timeout, or network error).
- **REQ-015**: MUST write the cache with an idle-delay of 86400 seconds after any failed HTTPS check (A-05).
- **REQ-016**: MUST provide `--get Path` printing the resolved value as one valid JSON document on stdout without decoration, labels, or confirmations.
- **REQ-017**: MUST provide `--set Path Value` parsing Value into the schema type and persisting the fully validated configuration atomically.
- **REQ-018**: MUST provide `--unset Path` restoring the targeted parameter or section to its schema default and persisting atomically.
- **REQ-019**: MUST provide `--print [Path]` rendering current values as a box-drawing tree whose section headings carry `[Path: <canonical path>]`.
- **REQ-020**: MUST provide `--info [Path]` rendering per-parameter type, constraints, description, default, and complete shell-valid `--set` and `--unset` command examples.
- **REQ-021**: MUST provide `--print-raw` writing the exact bytes of the global configuration JSON file to stdout without reformatting or added text.
- **REQ-022**: MUST resolve configuration paths as case-sensitive, colon-separated canonical tokens and reject unknown or misplaced tokens with a stderr diagnostic.
- **REQ-023**: MUST exit 1 with a clear stderr diagnostic on any configuration CLI failure, emit valid output on stdout only, and print nothing on failure.
- **REQ-024**: MUST define configuration section `Notifications` holding Selection parameter `new_version_color` (default `bright_green`) and Selection parameter `error_color` (default `bright_red`).
- **REQ-025**: MUST restrict both Selection parameters to the enum `bright_green`, `bright_red`, `bright_yellow`, `bright_blue`, `bright_magenta`, `bright_cyan`, `bright_white`.
- **REQ-026**: MUST color version-check notifications with the configured values and fall back to schema defaults when the configuration cannot be loaded.
- **REQ-027**: MUST format each `--ver` report row as `<label padded to 17 characters> : <version>`, rendering the labels `Current Installed`, `Latest @ PyPI`, and `Latest @ GitHub` with aligned version numbers.
- **REQ-028**: MUST fill the `Latest @ PyPI` report row with the latest version from `https://pypi.org/pypi/githubtemplateastraluv/json`.
- **REQ-029**: MUST fill the `Latest @ GitHub` report row with the latest release tag from `https://api.github.com/repos/Ogekuri/GitHub-Template-AstralUV/releases/latest`, stripped of its `v` prefix.
- **REQ-030**: MUST print `unavailable` in place of the version for a failed report source and a bright red note naming that source.
- **REQ-031**: MUST update the version-check cache from the report PyPI outcome only: 3600-second idle-delay on success, 86400-second idle-delay on failure.
- **REQ-032**: MUST execute `uv tool install githubtemplateastraluv --force --from git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` when `--upgrade --develop` or `--upgrade --dev` runs on Linux.
- **REQ-033**: MUST NOT execute any develop-upgrade command on non-Linux operating systems; MUST print a warning and the manual command of REQ-032 instead.
- **REQ-034**: MUST interpret `--develop` and `--dev` exclusively as source modifiers of `--upgrade`, leaving every other argument combination to the existing dispatch behavior.

## 4. Test Requirements
- **TST-001**: MUST verify REQ-001 by running the CLI with no arguments and with `--help`; pass iff stdout equals the 3.2 template with `(x.y.z)` replaced by the current version.
- **TST-002**: MUST verify REQ-002 by invoking `--ver` and asserting the three-row aligned report prints and the fetches execute even with an unexpired cache file.
- **TST-003**: MUST verify REQ-003, REQ-005, and REQ-032 on Linux (or a mocked platform) by asserting the exact PyPI, develop, and uninstall `uv` command strings execute.
- **TST-004**: MUST verify REQ-004, REQ-006, and REQ-033 by simulating a non-Linux platform and asserting no `uv` subprocess spawns while the warnings and manual commands print.
- **TST-005**: MUST verify REQ-007, REQ-008, and REQ-009 with a mocked PyPI endpoint: absent cache triggers one request; unexpired cache triggers none; timeout equals 2 seconds.
- **TST-006**: MUST verify REQ-010, REQ-011, REQ-012, and REQ-013 by mocking a newer-release response; pass iff bright green output prints and the cache holds four fields with idle-time equal to check time plus 3600.
- **TST-007**: MUST verify REQ-014 and REQ-015 by mocking an HTTP 503 response; pass iff a bright red error message prints and cache idle-time equals attempt time plus 86400.
- **TST-008**: MUST verify `--print` and `--info` against complete golden outputs covering sibling branches, leaf details, selection tables, and requested subtrees.
- **TST-009**: MUST verify tree structural invariants and table alignment: real-node edges match schema topology and every detail line carries its owner prefix.
- **TST-010**: MUST verify the configuration CLI by exercising `--get`, `--set`, `--unset`, `--print`, `--info`, and `--print-raw` for valid, invalid, and reset flows with isolated `$HOME`.
- **TST-011**: MUST verify REQ-026 by asserting default bright green and bright red notifications and configured-color rendering after `--set`.
- **TST-012**: MUST verify DES-015 and CTN-010 by parsing `.github/workflows/release-pypi.yml` and asserting every `uses:` pin meets the Node24-or-later runtime constraint with no fallback variable present.
- **TST-013**: MUST verify REQ-027 through REQ-031 with mocked PyPI and GitHub payloads: exact aligned rows, `unavailable` rows plus red notes on failures, and cache deltas driven only by the PyPI outcome.
- **TST-014**: MUST verify REQ-032, REQ-033, and REQ-034 by asserting the exact develop argv on Linux, the warning and manual command on non-Linux, and no upgrade dispatch for `--develop` alone.
- **TST-015**: MUST verify DES-016, DES-017, and DES-018 by parsing `.github/workflows/release-pypi.yml` and asserting the OIDC publish job with `id-token: write` runs only for `master` tags while build and release jobs run for every tag.
- **TST-016**: MUST verify DES-021, DES-022, DES-023, DES-024, and DES-025 by executing `./scripts/build.sh` twice; pass iff both runs exit 0, `dist/` holds exactly one sdist and one wheel, and stale artifacts do not accumulate.
- **TST-017**: MUST verify DES-026 through DES-038 by executing `./scripts/pre-release-check.sh`; pass iff exit code is 0 and `git status --porcelain --ignored` equals the pre-execution baseline.
- **TST-018**: MUST verify DES-027, DES-034, and DES-035 in an isolated repository copy with an injected failing tool; pass iff exit code is non-zero, the diagnostic names the failed phase, and no generated artifacts remain.
- **TST-019**: MUST verify DES-039 and DES-040 with `git check-ignore -v --no-index`; pass iff generated artifacts under `dist/` match the specific rules and `dist/` itself is not ignored.

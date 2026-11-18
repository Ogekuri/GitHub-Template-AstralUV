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
Project `githubtemplateastraluv`: a Python CLI application distributed as an Astral UV tool via `uv tool install` from `git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` or executed on-the-fly via `uvx`; the repository doubles as the GitHub template `Ogekuri/GitHub-Template-AstralUV` ("GitHub template for Astral-UV app", author Francesco Rolando).

Interface: text-only CLI in English; no GUI functionality is requested. Functional areas: management commands (`--help`, `--ver`, `--version`, `--upgrade`, `--uninstall`) independent from core logic; automatic online new-version check throttled by an idle-time JSON cache; colored console notifications. Configurability: version-check parameters (endpoint, timeout, and idle-delays) remain hardcoded constants and stay unexposed (CTN-008); the cache location derives from the `$HOME` environment variable; notification colors are user-configurable through a JSON configuration CLI (`--get`, `--set`, `--unset`, `--print`, `--info`, `--print-raw`) persisting state at `$HOME/.config/githubtemplateastraluv/config.json` (REQ-024). No application project-local configuration layer exists; the repository-root `.g.conf` file belongs to repository tooling and is not application configuration. Performance constraints: HTTPS timeout of 2 seconds; cache gating avoids redundant network calls.

Component model: the CLI entry `src/githubtemplateastraluv/__main__.py` dispatches to management commands and core logic; a dedicated version-check component performs the HTTPS query, cache persistence, and notification rendering before argument parsing; `scripts/templateastraluv.sh` wraps local execution.

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
- **PRJ-001**: MUST provide the Python CLI application `githubtemplateastraluv`, installable as an Astral UV tool via `uv` and executable on-the-fly via `uvx`.
- **PRJ-002**: MUST support local execution of the CLI through the launcher script `scripts/templateastraluv.sh`.
- **PRJ-003**: MUST provide text-based management commands `--help`, `--ver`, `--version`, `--upgrade`, and `--uninstall`, implemented independently from the core application logic.
- **PRJ-004**: MUST provide an automatic online new-version check that runs before CLI argument parsing and is throttled by an idle-time cache.
- **PRJ-005**: MUST provide a text-only CLI interface in English; no GUI functionality is required.
- **PRJ-006**: MUST provide configuration CLI commands `--get`, `--set`, `--unset`, `--print`, `--info`, and `--print-raw`, implemented additively without altering existing commands.

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
│       └── release-uvx.yml
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

- **REQ-002**: MUST print the current version in `x.y.z` format for `--ver` and `--version`, then force the online version check bypassing idle-delay and cache file.
- **REQ-003**: MUST execute `uv tool install githubtemplateastraluv --force --from git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` when `--upgrade` runs on Linux.
- **REQ-004**: MUST NOT execute any upgrade command on non-Linux operating systems; MUST print a warning and the manual command of REQ-003 instead.
- **REQ-005**: MUST execute `uv tool uninstall githubtemplateastraluv` when `--uninstall` runs on Linux.
- **REQ-006**: MUST NOT execute any uninstall command on non-Linux operating systems; MUST print a warning and the manual command of REQ-005 instead.
- **REQ-007**: MUST run the automatic version check before argument parsing on every invocation, subject to REQ-008 gating; `--ver` and `--version` bypass the gate.
- **REQ-008**: MUST perform the HTTPS request only when the cache file is absent or the current epoch is greater than or equal to the cached idle-time; otherwise skip the check.
- **REQ-009**: MUST query `https://api.github.com/repos/Ogekuri/GitHub-Template-AstralUV/releases/latest` with a 2-second timeout whenever the check executes.
- **REQ-010**: MUST persist, after every executed check, a cache JSON containing four fields: last-check epoch, last-check human-readable, idle-time epoch, idle-time human-readable.
- **REQ-011**: MUST compute the idle-time epoch as the last-check epoch plus the applicable idle-delay: 3600 seconds on success, 86400 seconds on failure.
- **REQ-012**: MUST print a bright green message comparing the available release version with the installed version when a newer release is found.
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

## 4. Test Requirements
- **TST-001**: MUST verify REQ-001 by running the CLI with no arguments and with `--help`; pass iff stdout equals the 3.2 template with `(x.y.z)` replaced by the current version.
- **TST-002**: MUST verify REQ-002 by invoking `--ver` and asserting stdout matches `^[0-9]+\.[0-9]+\.[0-9]+$` and the check executes even with an unexpired cache file.
- **TST-003**: MUST verify REQ-003 and REQ-005 on Linux (or a mocked platform) by asserting the exact `uv tool install` and `uv tool uninstall` command strings execute.
- **TST-004**: MUST verify REQ-004 and REQ-006 by simulating a non-Linux platform and asserting no `uv` subprocess spawns while the warning and manual command print.
- **TST-005**: MUST verify REQ-007, REQ-008, and REQ-009 with a mocked endpoint: absent cache triggers one request; unexpired cache triggers none; timeout equals 2 seconds.
- **TST-006**: MUST verify REQ-010, REQ-011, REQ-012, and REQ-013 by mocking a newer-release response; pass iff bright green output prints and the cache holds four fields with idle-time equal to check time plus 3600.
- **TST-007**: MUST verify REQ-014 and REQ-015 by mocking an HTTP 503 response; pass iff a bright red error message prints and cache idle-time equals attempt time plus 86400.
- **TST-008**: MUST verify `--print` and `--info` against complete golden outputs covering sibling branches, leaf details, selection tables, and requested subtrees.
- **TST-009**: MUST verify tree structural invariants and table alignment: real-node edges match schema topology and every detail line carries its owner prefix.
- **TST-010**: MUST verify the configuration CLI by exercising `--get`, `--set`, `--unset`, `--print`, `--info`, and `--print-raw` for valid, invalid, and reset flows with isolated `$HOME`.
- **TST-011**: MUST verify REQ-026 by asserting default bright green and bright red notifications and configured-color rendering after `--set`.

> [!CAUTION]
> **STRICTLY EXPERIMENTAL**: this project is a proof-of-concept template under
> active development. Interfaces, commands, packaging metadata, and release
> channels may change at any time without notice. Do not rely on it for
> production workloads.

# githubtemplateastraluv / templateastraluv (0.0.6)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-GPL--3.0-491?style=flat-square" alt="License: GPL-3.0">
  <img src="https://img.shields.io/badge/platform-Linux-6A7EC2?style=flat-square&logo=terminal&logoColor=white" alt="Platforms">
  <img src="https://img.shields.io/badge/docs-live-b31b1b" alt="Docs">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
</p>
<p align="center">
<strong>GitHub template for Astral-UV apps published on PyPI.</strong><br>
A Python CLI application shipped as an Astral uv/uvx-installable tool with
PyPI OIDC Trusted Publishing release automation. It provides management
commands for upgrade, uninstall, and version reporting; an automatic
new-version check throttled by an idle-time cache; self-upgrade from PyPI or
from the latest GitHub tag via <code>--develop</code>; a dual-source version
report (installed / PyPI / GitHub); and a JSON configuration CLI
(<code>version_check:disable-version-check</code>) with schema validation
and atomic persistence.
</p>

<p align="center">
  <a href="#feature-highlights">Feature Highlights</a> |
  <a href="#quick-start">Quick Start</a> |
  <a href="#requirements">Requirements</a> |
  <a href="#users-guide">User's Guide</a> |
  <a href="#acknowledgments">Acknowledgments</a>
</p>

<p align="center">
🚧 <strong>STAGE:</strong> PRE-ALPHA 📝 - Proof-of-Concept 🏗️ 🚧<br>
⚠️ <strong>IMPORTANT NOTICE</strong>: Created with <a href="https://github.com/Ogekuri/PI-useReq"><strong>PI-useReq/pi-usereq</strong></a> 🤖✨ ⚠️
</p>

# Feature Highlights

- **Published on PyPI**: install with `uv tool install githubtemplateastraluv`, or run on-the-fly with `uvx githubtemplateastraluv`.
- **Dual-source version report** (`--ver` / `--version`): installed, latest PyPI, and latest GitHub versions in aligned columns.
- **Automatic new-version check** before every run, throttled by an idle-time cache so no redundant network calls are made.
- **Self-upgrade** from PyPI (`--upgrade`), forced full re-download (`--force`), or the latest GitHub tagged release (`--develop`).
- **One-command removal** (`--uninstall`) — on non-Linux systems the exact manual command is printed instead.
- **Colored console notifications** (bright green for availability, bright red for errors), hardcoded in the embedded internal color JSON of `src/githubtemplateastraluv/colors.py`.
- **Configuration CLI** (`--get`, `--set`, `--unset`, `--print`, `--info`, `--print-raw`) with schema validation and atomic persistence.
- **Release automation**: a GitHub release for every version tag and OIDC Trusted Publishing to PyPI for `master` tags.

# Quick Start

1. **Install** the tool from PyPI:

   ```bash
   uv tool install githubtemplateastraluv
   ```

2. **Configure** — optional: the application works out of the box with
   sensible defaults (bright green availability notes, bright red error
   notes). Customization is described in the [User's Guide](#users-guide).

3. **Execute**:

   ```bash
   githubtemplateastraluv --help
   githubtemplateastraluv --ver
   ```

# Requirements

- **Python >= 3.11**.
- **Astral `uv`** — required to install, upgrade, uninstall, or run the tool locally from the repository.
- **`git`** — required only to install the development source with `--develop`.
- **Network access** — outbound HTTPS to `pypi.org` (version check, upgrades) and `api.github.com` (latest-release query for the `--ver` report and `--develop` channel).
- **Linux** — required for the `--upgrade` and `--uninstall` side effects; on any other platform the tool prints a warning and the exact manual command.
- **ANSI-capable terminal** — required for colored notifications.

# User's Guide

## Install from PyPI (primary method)

```bash
uv tool install githubtemplateastraluv
```

Upgrade and uninstall:

```bash
githubtemplateastraluv --upgrade
uv tool uninstall githubtemplateastraluv
```

## Live execution with uvx (alternative method)

Run directly from PyPI without a prior installation:

```bash
uvx githubtemplateastraluv
uvx githubtemplateastraluv --ver
```

## Install and upgrade from GitHub (non-primary development channel)

A dedicated, non-primary distribution channel hosts intermediate and test
releases on GitHub: `https://github.com/Ogekuri/GitHub-Template-AstralUV`.

```bash
# Install from the GitHub repository
uv tool install githubtemplateastraluv --force --from git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git

# Upgrade to the latest GitHub tagged release (tagged on any branch)
githubtemplateastraluv --upgrade --develop

# Forced full re-download and reinstallation variants
githubtemplateastraluv --upgrade --force
githubtemplateastraluv --upgrade --develop --force
```

`--upgrade --develop` always downloads the most recent tagged build from
GitHub, regardless of the branch it was tagged on. The `--ver` report shows
that channel in the `Latest @ GitHub` row.

## Run locally from the repository

```bash
./scripts/templateastraluv.sh --help
```

The launcher resolves the repository root and delegates to
`uv run --project <root> python -m githubtemplateastraluv`.

## Command reference

The full help screen (printed by `--help` or by running the tool with no
arguments):

```text
Usage: githubtemplateastraluv [command] [options] (0.0.6)

Management Commands:
  --upgrade   - Reinstall githubtemplateastraluv on Linux; print manual command elsewhere.
  --uninstall - Uninstall githubtemplateastraluv on Linux; print manual command elsewhere.
  --ver       - Print the githubtemplateastraluv version.
  --version   - Print the githubtemplateastraluv version.
  --help      - Print the full help screen.

Configuration Commands:
  --get       - Print the value at Path as one JSON document.
  --set       - Parse Value into the schema type and persist it at Path.
  --unset     - Restore Path to its schema default and persist atomically.
  --print     - Print current values as a box-drawing tree, whole schema or at Path.
  --info      - Print parameter documentation with defaults, constraints, and examples.
  --print-raw - Print the exact bytes of the configuration JSON file.

Options:
  --develop   - With --upgrade: install from the GitHub development source.
  --force     - With --upgrade: force full re-download and reinstallation.
```

### Version report (`--ver` / `--version`)

Prints the three-row report with aligned version columns and always refreshes
the source queries, bypassing the idle-time gate:

```text
Current Installed : X1.Y1.Z1
Latest @ PyPI     : X2.Y2.Z2
Latest @ GitHub   : X3.Y3.Z3
```

A failed source prints `unknown (<reason>)` in place of the version, with a
bright red note naming that source. The GitHub row strips the `v` prefix from
the latest release tag.

### `--upgrade` variants (Linux)

| Command | Executed command |
| --- | --- |
| `--upgrade` | `uv tool upgrade githubtemplateastraluv` |
| `--upgrade --force` | `uv tool install githubtemplateastraluv --force --reinstall --refresh` |
| `--upgrade --develop` | `uv tool install githubtemplateastraluv --reinstall --from git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` |
| `--upgrade --develop --force` | `uv tool install githubtemplateastraluv --force --reinstall --refresh --from git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` |

On non-Linux operating systems nothing is executed: the tool prints a warning
and the matching manual command from the table. `--develop` and `--force` are
accepted exclusively as `--upgrade` modifiers; any other combination falls
back to the normal dispatch behavior.

### `--uninstall` (Linux)

```bash
githubtemplateastraluv --uninstall
```

Executes `uv tool uninstall githubtemplateastraluv` on Linux; on any other
platform it prints a warning and the manual command
`uv tool uninstall githubtemplateastraluv`.

## Configuration

### Configuration file

The global configuration lives at
`$HOME/.config/githubtemplateastraluv/config.json`. It is created with the
schema defaults on the first configuration command and every update is
validated against the schema and persisted atomically (the previous file is
preserved if any step fails).

### Configuration commands

Configuration paths are case-sensitive, colon-separated canonical tokens
(`Section`, `Section:Parameter`); the schema defines the `version_check`
section holding the `disable-version-check` Selection parameter.

| Command | Behavior |
| --- | --- |
| `--get <Path>` | Prints the resolved value as one valid JSON document on stdout. |
| `--set <Path> <Value>` | Parses `Value` into the schema type, validates, and persists atomically. |
| `--unset <Path>` | Restores the targeted parameter or section to its schema default. |
| `--print [Path]` | Renders current values as a box-drawing tree with `[Path: <canonical path>]` section headings. |
| `--info [Path]` | Renders per-parameter type, constraints, description, default, and shell-valid `--set` / `--unset` examples. |
| `--print-raw` | Writes the exact bytes of the configuration JSON file to stdout. |

Examples:

```bash
githubtemplateastraluv --print
githubtemplateastraluv --info
githubtemplateastraluv --print-raw

# Read, change, and restore the automatic version-check switch.
githubtemplateastraluv --get version_check:disable-version-check
githubtemplateastraluv --set version_check:disable-version-check yes
githubtemplateastraluv --unset version_check:disable-version-check
```

On any configuration failure the tool exits with code `1`, prints a
diagnostic on stderr, and emits nothing on stdout.

### Notification colors (hardcoded)

Notification colors are not configurable. All colors live in one embedded
internal JSON document (`COLOR_CONFIG_JSON`) inside
`src/githubtemplateastraluv/colors.py`:

- `notifications` assigns the new-version color `bright_green` (ANSI SGR 92)
  and the error color `bright_red` (ANSI SGR 91).
- `palette` maps every color token to its ANSI SGR prefix: `bright_green`
  (92), `bright_red` (91), `bright_yellow` (93), `bright_blue` (94),
  `bright_magenta` (95), `bright_cyan` (96), `bright_white` (97).

Both colors drive the automatic version-check notifications; no CLI option,
file, or environment variable can alter them.

# Documentation

## Automatic version check

On every invocation the tool runs an online new-version check **before**
argument parsing. The check is throttled by an idle-time cache:

- Cache file: `$HOME/.cache/githubtemplateastraluv/check_version_idle-time.json`.
- The HTTPS request to `https://pypi.org/pypi/githubtemplateastraluv/json` runs
  only when the cache file is absent or the cached idle-time has elapsed
  (2-second timeout).
- A successful check refreshes the cache with a 3600-second idle-delay; a
  failed check (HTTP 429, 503, timeout, network error) reports a bright red
  error note and backs off with an 86400-second idle-delay.
- `--ver` and `--version` bypass the gate and always query both sources
  (PyPI JSON API and `https://api.github.com/repos/Ogekuri/GitHub-Template-AstralUV/releases/latest`).

## Repository tooling scripts

| Script | Purpose |
| --- | --- |
| `scripts/templateastraluv.sh` | Local-run launcher delegating to `uv run --project <root> python -m githubtemplateastraluv`. |
| `scripts/build.sh` | Release packager: cleans the generated state, removes stale `dist/*.tar.gz`/`dist/*.whl`, builds `uv run --frozen --with build python -m build`, and verifies the produced sdist and wheel. |
| `scripts/clean.sh` | Removes every repository-internal execution-generated artifact and restores the canonical startup state. |
| `scripts/pre-release-check.sh` | Fail-fast release verification (syntax, compileall, pytest, out-of-tree build, artifact validation) with baseline-guarded cleanup. |

`scripts/clean.sh` removes `__pycache__/` and `*.egg-info/` at any depth,
the `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `build/`, and
`.venv/` directories, and the `.coverage`/`.coverage.*` data files. It is
idempotent (absent targets are a successful no-op), never touches tracked
files, untracked user files, `$HOME` application data, or the versioned
release artifacts in `dist/`, and never runs destructive git commands.

```bash
# Remove all execution-generated temporary artifacts
./scripts/clean.sh

# Build from the canonical cleaned state (also via clean.sh)
./scripts/build.sh
```

## Release automation

For every canonical version tag `vX.Y.Z` the release workflow
(`.github/workflows/release-pypi.yml`) creates a GitHub release from the
`dist/` artifacts present at the tagged commit and, when the tag belongs to
`master`, publishes them to PyPI through OIDC Trusted Publishing. No build
step runs inside the workflow; runners are pinned to `ubuntu-24.04`.

## Using this repository as a template

This repository doubles as the GitHub template
[`Ogekuri/GitHub-Template-AstralUV`](https://github.com/Ogekuri/GitHub-Template-AstralUV)
for new Astral-UV applications. Template initialization extracts a skeleton
bundle into the working directory and resolves seven keywords
(`%AUTHOR%`, `%DESCRIPTION%`, `%PROGRAM%`, `%SHORTNAME%`, `%SRCDIR%`,
`%OWNER%`, `%REPOSITORY%`) across the repository files, then renames the
skeleton script and package directories to the substituted names. The full
procedure is specified in `usereq/docs/REQUIREMENTS.md`.

## Development and testing

```bash
# Run the unit-test suite
uv run pytest

# Full release-readiness verification (fail-fast, leaves no artifacts)
./scripts/pre-release-check.sh
```

The test suite covers the help screen, version report, management-command
argv variants, the gated version check and its cache, the configuration CLI,
the release-workflow contract, and the packaging artifacts.

# License

This project is licensed under the **GNU General Public License v3.0 only**
(SPDX identifier `GPL-3.0-only`), as declared in `pyproject.toml`.
The full license text is available in the [`LICENSE`](LICENSE) file.

Copyright (c) Francesco Rolando.

# Acknowledgments

- **[Astral](https://github.com/astral-sh/uv)** — for `uv` and `uvx`, the packaging and distribution backbone of this template.
- **[PI-useReq](https://github.com/Ogekuri/PI-useReq)** — the requirement-driven agentic workflow used to specify, implement, and document this repository.
- **[PyPA](https://github.com/pypa)** — for `build` and the Python packaging standards used by the release pipeline.
- **[Shields.io](https://shields.io)** — for the README badges.

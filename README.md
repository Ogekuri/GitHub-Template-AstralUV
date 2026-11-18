# githubtemplateastraluv/templateastraluv (0.0.0)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-GPL--3.0-491?style=flat-square" alt="License: GPL-3.0">
  <img src="https://img.shields.io/badge/platform-Linux-6A7EC2?style=flat-square&logo=terminal&logoColor=white" alt="Platforms">
  <img src="https://img.shields.io/badge/docs-live-b31b1b" alt="Docs">
<img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
</p>
<p align="center">
<strong>GitHub template for Astral-UV apps published on PyPI.</strong><br>
Python CLI template with Astral uv/uvx packaging, PyPI OIDC Trusted
Publishing release automation, self-upgrade from PyPI (or the latest
GitHub tag via <code>--develop</code>), and a dual-source version report.
</p>


<p align="center">
  <a href="#quick-start">Quick Start</a> |
  <a href="#feature-highlights">Feature Highlights</a> |
  <a href="#acknowledgments">Acknowledgments</a>
</p>

<p align="center">
<br>
🚧 <strong>DRAFT</strong>: 👾 Alpha Development 👾 - Work in Progress 🏗️ 🚧<br>
⚠️ <strong>IMPORTANT NOTICE</strong>: Created with <a href="https://github.com/ogekuri/useReq"><strong>useReq/req</strong></a> 🤖✨ ⚠️<br>
<br>
<p>


## Feature Highlights
- Published on PyPI: install with `uv tool install githubtemplateastraluv`.
- Automatic online new-version check (PyPI) throttled by an idle-time cache.
- `--ver` dual-source report: installed, latest PyPI, and latest GitHub versions, with aligned columns.
- Self-upgrade from PyPI; `--upgrade --develop` pulls the latest GitHub tagged release.
- Colored console notifications with user-configurable colors.
- Release automation: GitHub release for every version tag; OIDC Trusted Publishing to PyPI for `master` tags only.


## Quick Start

1. Install the tool from PyPI:
```bash
uv tool install githubtemplateastraluv
```
2. Run it:
```bash
githubtemplateastraluv --help
```

## Usage

```bash
# Print the version report (aligned columns)
githubtemplateastraluv --ver
```

Output format:
```
Current Installed : X1.Y1.Z1
Latest @ PyPI     : X2.Y2.Z2
Latest @ GitHub   : X3.Y3.Z3
```

```bash
# Upgrade from PyPI (Linux; prints the manual command elsewhere)
githubtemplateastraluv --upgrade

# Upgrade to the latest GitHub tagged release (any branch)
githubtemplateastraluv --upgrade --develop   # alias: --dev

# Uninstall (Linux; prints the manual command elsewhere)
githubtemplateastraluv --uninstall

# Full help screen
githubtemplateastraluv --help
```


## Install with Astral uv (PyPI — primary method)

#### Install
```bash
uv tool install githubtemplateastraluv
```

#### Upgrade
```bash
githubtemplateastraluv --upgrade
```

#### Uninstall
```bash
uv tool uninstall githubtemplateastraluv
```

## Live execution with uvx (alternative method)

Run githubtemplateastraluv directly from PyPI without prior installation:

```bash
uvx githubtemplateastraluv
```

You can pass options as usual, for example:

```bash
uvx githubtemplateastraluv <args>
```

## Install and upgrade from GitHub (development releases)

A dedicated, non-primary distribution channel hosts intermediate and test
releases on GitHub: `https://github.com/Ogekuri/GitHub-Template-AstralUV`.

#### Install
```bash
uv tool install githubtemplateastraluv --force --from git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git
```

#### Upgrade to the latest GitHub tagged release (any branch)
```bash
githubtemplateastraluv --upgrade --develop
```

`--upgrade --develop` (alias `--dev`) always downloads the most recent
tagged build from GitHub, regardless of the branch it was tagged on
(`master`, `develop`, or any other branch). The `--ver` report shows the
GitHub latest release in the `Latest @ GitHub` row.
```


## Acknowledgments

TODO: fill scknowledgments section


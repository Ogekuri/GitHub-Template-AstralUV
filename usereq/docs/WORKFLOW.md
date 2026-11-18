# githubtemplateastraluv Runtime Workflow

Runtime model derived from static analysis of `src/` only. Declaration file
paths only; no line numbers. Process IDs are stable.

## Execution Units Index

| ID | Type | Parent process | Role | Entrypoint symbol(s) | Defining file(s) |
| --- | --- | --- | --- | --- | --- |
| `PROC:launcher` | process | none (user shell) | Local-run wrapper resolving the project root and delegating to the uv runtime | `scripts/templateastraluv.sh` (bash top-level execution) | `scripts/templateastraluv.sh` |
| `PROC:uv-runtime` | process | `PROC:launcher` | Transient uv process that resolves/creates the project virtual environment and launches the CLI | uv CLI argv: `run --project <BASE_DIR> python -m githubtemplateastraluv` | `scripts/templateastraluv.sh` |
| `PROC:main` | process | `PROC:uv-runtime` (via launcher) or user interpreter | CLI application process: gated version check plus management-command dispatch | `githubtemplateastraluv.__main__:main`; module guard `python -m githubtemplateastraluv` | `src/githubtemplateastraluv/__main__.py`, `src/githubtemplateastraluv/core.py` |
| `PROC:uv-tool-manage` | process | `PROC:main` | Transient child process executing `uv tool install` / `uv tool uninstall` (Linux only) | uv CLI argv from `UPGRADE_COMMAND` / `UNINSTALL_COMMAND` | `src/githubtemplateastraluv/management.py` |

Threads: `PROC:main` — no explicit threads detected. `PROC:launcher`,
`PROC:uv-runtime`, `PROC:uv-tool-manage` — no explicit threads detected.

## Execution Units

### PROC:launcher

- Entrypoint(s): bash interpreter executing `scripts/templateastraluv.sh`
  top-level statements.
- Lifecycle/trigger: starts on user invocation of
  `scripts/templateastraluv.sh`; resolves the absolute script path, derives
  the base and project root directories, rejects execution when the base
  directory differs from the git root, then replaces itself with the uv
  runtime process via `exec` (or exits non-zero on root-resolution
  failure).
- Internal Call-Trace Tree: no internal functions under `src/` (linear
  top-level shell script; no function definitions).
- External Boundaries: `readlink -f`, `dirname`, `basename`, `git
  rev-parse --show-toplevel`, `exec` process replacement, uv CLI
  invocation, stderr diagnostics.

### PROC:uv-runtime

- Entrypoint(s): `uv run --project <BASE_DIR> python -m
  githubtemplateastraluv`.
- Lifecycle/trigger: starts when `PROC:launcher` execs uv; resolves or
  creates the project virtual environment, then spawns `PROC:main`;
  blocks until the CLI process ends and exits with its status.
- Internal Call-Trace Tree: none under `src/` (external tooling process).
- External Boundaries: virtual-environment filesystem, Python interpreter
  spawn, uv package cache.

### PROC:main

- Entrypoint(s): console-script entry `githubtemplateastraluv.__main__:main`
  and the module guard in `src/githubtemplateastraluv/__main__.py`
  (`sys.exit(main())`).
- Lifecycle/trigger: starts on CLI invocation; optionally runs the gated
  online version check before dispatch (forced variant for `--ver` /
  `--version`), prints help/version or executes install/uninstall
  management commands, and terminates through `sys.exit` with the
  dispatcher return code.
- Internal Call-Trace Tree (internal functions only, call order):
  - `main(...)`: gated check, then command dispatch
    [`src/githubtemplateastraluv/core.py`]
    - `version_check.run_version_check(...)`: online check orchestration
      [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._cache_path(...)`: resolve cache file path from
        `$HOME` [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._read_cache(...)`: load idle-time cache JSON
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._gate_allows_request(...)`: idle-time request gate
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._fetch_latest_release(...)`: HTTPS GET of the
        latest release tag [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._parse_version(...)`: dotted-version compare key
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._report_failure(...)`: bright-red note plus 86400 s
        backoff cache [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._print_colored(...)`: ANSI-colored stdout print
          [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._write_cache(...)`: persist four-field cache
          [`src/githubtemplateastraluv/version_check.py`]
          - `version_check._human_timestamp(...)`: UTC ISO-8601 rendering
            [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._print_colored(...)`: bright-green availability
        note [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._write_cache(...)`: 3600 s refresh cache
        [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._human_timestamp(...)`
          [`src/githubtemplateastraluv/version_check.py`]
    - `management.print_help(...)`: print full help screen
      [`src/githubtemplateastraluv/management.py`]
      - `management.build_help_text(...)`: assemble REQ-001 template
        [`src/githubtemplateastraluv/management.py`]
        - `management._management_entry(...)`: render one aligned command
          line [`src/githubtemplateastraluv/management.py`]
    - `management.cmd_upgrade(...)`: Linux-only `uv tool install` with
      manual-command fallback [`src/githubtemplateastraluv/management.py`]
      - `management.is_linux(...)`: platform check
        [`src/githubtemplateastraluv/management.py`]
    - `management.cmd_uninstall(...)`: Linux-only `uv tool uninstall`
      with manual-command fallback
      [`src/githubtemplateastraluv/management.py`]
      - `management.is_linux(...)`
        [`src/githubtemplateastraluv/management.py`]
- External Boundaries: HTTPS GitHub API endpoint; cache JSON file under
  `$HOME/.cache/githubtemplateastraluv/`; stdout (help, version, colored
  notifications); `subprocess.run` spawn of the uv CLI (management
  commands, Linux only); `sys.argv`; `HOME` environment variable.

### PROC:uv-tool-manage

- Entrypoint(s): `uv tool install githubtemplateastraluv --force --from
  git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` or `uv
  tool uninstall githubtemplateastraluv`.
- Lifecycle/trigger: spawned by `PROC:main` only when `is_linux()` is
  true and the user passed `--upgrade` or `--uninstall`; runs to
  completion; its return code propagates to `PROC:main` as the CLI exit
  code.
- Internal Call-Trace Tree: none under `src/` (external tooling process).
- External Boundaries: uv tool environment, PyPI/Git install sources,
  inherited stdio.

## Communication Edges

| # | Direction | Mechanism | Endpoint / Channel | Payload / Data shape | Declaration file path(s) |
| --- | --- | --- | --- | --- | --- |
| 1 | `PROC:launcher` -> `PROC:uv-runtime` | process `exec` replacement, stdio inherited | uv CLI (`run --project`) | argv: base directory, `python -m githubtemplateastraluv`, user arguments | `scripts/templateastraluv.sh` |
| 2 | `PROC:uv-runtime` -> `PROC:main` | child-process spawn, stdio inherited | `python -m githubtemplateastraluv` execution | argv passthrough; CLI exit status returned to uv | `scripts/templateastraluv.sh`, `src/githubtemplateastraluv/__main__.py` |
| 3 | `PROC:main` -> `PROC:uv-tool-manage` | `subprocess.run` spawn, stdio inherited | uv CLI `tool install` / `tool uninstall` | `UPGRADE_COMMAND` / `UNINSTALL_COMMAND` argv; `returncode` propagated | `src/githubtemplateastraluv/management.py` |
| 4 | `PROC:main` -> GitHub API (network) | HTTPS GET via `urllib.request.urlopen`, 2 s timeout | `https://api.github.com/repos/Ogekuri/GitHub-Template-AstralUV/releases/latest` | JSON object with `tag_name` release tag | `src/githubtemplateastraluv/version_check.py` |
| 5 | `PROC:main` -> filesystem (cache) | JSON file read/write with parent-directory creation | `$HOME/.cache/githubtemplateastraluv/check_version_idle-time.json` | four-field JSON: `last_check_epoch`, `last_check_human`, `idle_time_epoch`, `idle_time_human` | `src/githubtemplateastraluv/version_check.py` |
| 6 | `PROC:main` -> stdout | `print()` (optionally ANSI SGR bright green 92 / bright red 91) | console stdout | help screen text, `x.y.z` version string, availability/error notifications | `src/githubtemplateastraluv/core.py`, `src/githubtemplateastraluv/management.py`, `src/githubtemplateastraluv/version_check.py` |
| 7 | `PROC:launcher` -> stderr | shell `echo` diagnostics | console stderr | project-root resolution errors | `scripts/templateastraluv.sh` |

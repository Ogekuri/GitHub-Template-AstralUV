# githubtemplateastraluv Runtime Workflow

Runtime model derived from static analysis of `src/` only. Declaration file
paths only; no line numbers. Process IDs are stable.

## Execution Units Index

| ID | Type | Parent process | Role | Entrypoint symbol(s) | Defining file(s) |
| --- | --- | --- | --- | --- | --- |
| `PROC:launcher` | process | none (user shell) | Local-run wrapper resolving the project root and delegating to the uv runtime | `scripts/templateastraluv.sh` (bash top-level execution) | `scripts/templateastraluv.sh` |
| `PROC:uv-runtime` | process | `PROC:launcher` | Transient uv process that resolves/creates the project virtual environment and launches the CLI | uv CLI argv: `run --project <BASE_DIR> python -m githubtemplateastraluv` | `scripts/templateastraluv.sh` |
| `PROC:main` | process | `PROC:uv-runtime` (via launcher) or user interpreter | CLI application process: gated version check plus management-command and configuration-CLI dispatch | `githubtemplateastraluv.__main__:main`; module guard `python -m githubtemplateastraluv` | `src/githubtemplateastraluv/__main__.py`, `src/githubtemplateastraluv/core.py`, `src/githubtemplateastraluv/config.py`, `src/githubtemplateastraluv/config_render.py` |
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
  online version check before dispatch (dual-source version report
  variant for `--ver` / `--version`), prints help, prints the aligned
  three-row version report, executes install/uninstall
  management commands, executes the configuration CLI commands
  (`--get`, `--set`, `--unset`, `--print-raw`, `--print`, `--info`),
  and terminates through `sys.exit` with the dispatcher return code.
- Internal Call-Trace Tree (internal functions only, call order):
  - `main(...)`: gated check, then command dispatch
    [`src/githubtemplateastraluv/core.py`]
    - `version_check.run_version_check(...)`: online check orchestration
      [`src/githubtemplateastraluv/version_check.py`]
      - `config.notification_colors(...)`: configured ANSI colors with
        schema-default fallback [`src/githubtemplateastraluv/config.py`]
        - `config.load_tolerant(...)`: defaults on any load failure
          [`src/githubtemplateastraluv/config.py`]
          - `config.load_strict(...)`: read, parse, and validate the
            global configuration
            [`src/githubtemplateastraluv/config.py`]
            - `config.config_path(...)`: resolve the configuration file
              path from `$HOME`
              [`src/githubtemplateastraluv/config.py`]
            - `config.validate_config(...)`: strict whole-schema
              validation [`src/githubtemplateastraluv/config.py`]
          - `config.default_config(...)`: build the schema-default
            payload [`src/githubtemplateastraluv/config.py`]
      - `version_check._cache_path(...)`: resolve cache file path from
        `$HOME` [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._read_cache(...)`: load idle-time cache JSON
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._gate_allows_request(...)`: idle-time request gate
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._fetch_latest_pypi_version(...)`: HTTPS GET of
        the latest PyPI version
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._parse_version(...)`: dotted-version compare key
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._report_failure(...)`: configured-color failure
        note plus 86400 s backoff cache
        [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._print_colored(...)`: ANSI-colored stdout print
          [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._write_cache(...)`: persist four-field cache
          [`src/githubtemplateastraluv/version_check.py`]
          - `version_check._human_timestamp(...)`: UTC ISO-8601 rendering
            [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._print_colored(...)`: configured-color availability
        note [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._write_cache(...)`: 3600 s refresh cache
        [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._human_timestamp(...)`
          [`src/githubtemplateastraluv/version_check.py`]
    - `version_check.run_version_report(...)`: forced dual-source version
      report for `--ver` / `--version`, gate and cache-file reads
      bypassed [`src/githubtemplateastraluv/version_check.py`]
      - `config.notification_colors(...)`: configured ANSI colors with
        schema-default fallback (same subtree as under
        `run_version_check`) [`src/githubtemplateastraluv/config.py`]
      - `version_check._fetch_latest_pypi_version(...)`: HTTPS GET of
        the latest PyPI version
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._fetch_latest_github_version(...)`: HTTPS GET of
        the latest GitHub release tag stripped of its `v` prefix
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._print_colored(...)`: bright red note naming the
        failed source [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._format_report_row(...)`: label-padded report row
        with aligned version columns
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._write_cache(...)`: 3600 s / 86400 s cache driven
        by the PyPI outcome only
        [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._human_timestamp(...)`
          [`src/githubtemplateastraluv/version_check.py`]
    - `management.print_help(...)`: print full help screen
      [`src/githubtemplateastraluv/management.py`]
      - `management.build_help_text(...)`: assemble REQ-001 template
        [`src/githubtemplateastraluv/management.py`]
        - `management._management_entry(...)`: render one aligned command
          line [`src/githubtemplateastraluv/management.py`]
    - `management.cmd_upgrade(...)`: Linux-only `uv tool install` from
      PyPI, or from GitHub for the `--develop` / `--dev` variant, with
      manual-command fallback
      [`src/githubtemplateastraluv/management.py`]
      - `management.is_linux(...)`: platform check
        [`src/githubtemplateastraluv/management.py`]
    - `management.cmd_uninstall(...)`: Linux-only `uv tool uninstall`
      with manual-command fallback
      [`src/githubtemplateastraluv/management.py`]
      - `management.is_linux(...)`
        [`src/githubtemplateastraluv/management.py`]
    - `config.handle_get(...)`: print one canonical path value as JSON
      [`src/githubtemplateastraluv/config.py`]
      - `config.operand_values(...)`: flag operand extraction and count
        validation [`src/githubtemplateastraluv/config.py`]
      - `config.ensure_bootstrapped(...)`: create directories and
        initialize defaults [`src/githubtemplateastraluv/config.py`]
        - `config.config_path(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.atomic_write_json(...)`: atomic durable JSON write
          [`src/githubtemplateastraluv/config.py`]
      - `config.load_strict(...)`
        [`src/githubtemplateastraluv/config.py`]
        - `config.config_path(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.validate_config(...)`
          [`src/githubtemplateastraluv/config.py`]
      - `config.resolve_segments(...)`: schema-driven canonical path
        resolution [`src/githubtemplateastraluv/config.py`]
      - `config.get_value(...)`: extract the JSON value at resolved
        segments [`src/githubtemplateastraluv/config.py`]
    - `config.handle_set(...)`: parse, validate, and atomically persist
      a value [`src/githubtemplateastraluv/config.py`]
      - `config.operand_values(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.ensure_bootstrapped(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.load_strict(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.set_value(...)`: apply a validated `--set` mutation
        [`src/githubtemplateastraluv/config.py`]
        - `config.resolve_segments(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.parse_value(...)`: parse one operand into the schema
          type [`src/githubtemplateastraluv/config.py`]
        - `config.validate_config(...)`
          [`src/githubtemplateastraluv/config.py`]
      - `config.atomic_write_json(...)`
        [`src/githubtemplateastraluv/config.py`]
    - `config.handle_unset(...)`: restore defaults and atomically persist
      [`src/githubtemplateastraluv/config.py`]
      - `config.operand_values(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.ensure_bootstrapped(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.load_strict(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.unset_value(...)`: apply a restore-to-default mutation
        [`src/githubtemplateastraluv/config.py`]
        - `config.resolve_segments(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.default_config(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.validate_config(...)`
          [`src/githubtemplateastraluv/config.py`]
      - `config.atomic_write_json(...)`
        [`src/githubtemplateastraluv/config.py`]
    - `config.handle_print_raw(...)`: emit exact configuration file bytes
      [`src/githubtemplateastraluv/config.py`]
      - `config.operand_values(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.ensure_bootstrapped(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.config_path(...)`
        [`src/githubtemplateastraluv/config.py`]
    - `config_render.handle_print(...)`: render current values as a tree
      [`src/githubtemplateastraluv/config_render.py`]
      - `config.operand_values(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.ensure_bootstrapped(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.load_strict(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config_render.build_print_root(...)`: build the display node
        tree [`src/githubtemplateastraluv/config_render.py`]
        - `config.resolve_segments(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config_render.format_table(...)`: measured-width rectangular
          table [`src/githubtemplateastraluv/config_render.py`]
          - `config_render.display_width(...)`: terminal cell width
            [`src/githubtemplateastraluv/config_render.py`]
      - `config_render.render_tree(...)`: canonical prefix-algorithm
        traversal [`src/githubtemplateastraluv/config_render.py`]
        - `config_render._emit_node(...)`: recursive node emitter
          [`src/githubtemplateastraluv/config_render.py`]
    - `config_render.handle_info(...)`: render schema documentation as a
      tree [`src/githubtemplateastraluv/config_render.py`]
      - `config.operand_values(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.ensure_bootstrapped(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config.load_strict(...)`
        [`src/githubtemplateastraluv/config.py`]
      - `config_render.build_info_root(...)`: build the documentation
        node tree [`src/githubtemplateastraluv/config_render.py`]
        - `config.resolve_segments(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.default_config(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config_render.format_table(...)`
          [`src/githubtemplateastraluv/config_render.py`]
      - `config_render.render_tree(...)`
        [`src/githubtemplateastraluv/config_render.py`]
- External Boundaries: HTTPS PyPI JSON API endpoint (gated check, report);
  HTTPS GitHub releases API endpoint (report; develop source of
  `--upgrade`); cache JSON file under
  `$HOME/.cache/githubtemplateastraluv/`; configuration JSON file under
  `$HOME/.config/githubtemplateastraluv/`; stdout (help, three-row
  version report, colored
  notifications, configuration JSON/trees/tables/raw bytes); stderr
  (configuration diagnostics); `subprocess.run` spawn of the uv CLI
  (management commands, Linux only); `sys.argv`; `HOME` environment
  variable.

### PROC:uv-tool-manage

- Entrypoint(s): `uv tool install githubtemplateastraluv --force` (PyPI
  source), `uv tool install githubtemplateastraluv --force --from
  git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` (develop
  variant), or `uv tool uninstall githubtemplateastraluv`.
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
| 3 | `PROC:main` -> `PROC:uv-tool-manage` | `subprocess.run` spawn, stdio inherited | uv CLI `tool install` / `tool uninstall` | `UPGRADE_COMMAND` / `UPGRADE_DEVELOP_COMMAND` / `UNINSTALL_COMMAND` argv; `returncode` propagated | `src/githubtemplateastraluv/management.py` |
| 4 | `PROC:main` -> PyPI (network) | HTTPS GET via `urllib.request.urlopen`, 2 s timeout | `https://pypi.org/pypi/githubtemplateastraluv/json` | JSON object with `info.version` latest published version | `src/githubtemplateastraluv/version_check.py` |
| 5 | `PROC:main` -> GitHub API (network) | HTTPS GET via `urllib.request.urlopen`, 2 s timeout | `https://api.github.com/repos/Ogekuri/GitHub-Template-AstralUV/releases/latest` | JSON object with `tag_name` release tag | `src/githubtemplateastraluv/version_check.py` |
| 6 | `PROC:main` -> filesystem (cache) | JSON file read/write with parent-directory creation | `$HOME/.cache/githubtemplateastraluv/check_version_idle-time.json` | four-field JSON: `last_check_epoch`, `last_check_human`, `idle_time_epoch`, `idle_time_human` | `src/githubtemplateastraluv/version_check.py` |
| 7 | `PROC:main` -> stdout | `print()` (optionally ANSI SGR configured colors, default bright green 92 / bright red 91) | console stdout | help screen text, three-row aligned version report, availability/error notifications, configuration JSON (`--get`), configuration trees (`--print`/`--info`), raw file bytes (`--print-raw`) | `src/githubtemplateastraluv/core.py`, `src/githubtemplateastraluv/management.py`, `src/githubtemplateastraluv/version_check.py`, `src/githubtemplateastraluv/config.py`, `src/githubtemplateastraluv/config_render.py` |
| 8 | `PROC:launcher` -> stderr | shell `echo` diagnostics | console stderr | project-root resolution errors | `scripts/templateastraluv.sh` |
| 9 | `PROC:main` -> filesystem (configuration) | JSON file read/write with parent-directory creation, temporary-file fsync, and `os.replace` atomic swap | `$HOME/.config/githubtemplateastraluv/config.json` | validated one-section JSON object: `Notifications` holding `new_version_color` and `error_color` selection tokens; raw bytes for `--print-raw` | `src/githubtemplateastraluv/config.py` |
| 10 | `PROC:main` -> stderr | `print(..., file=sys.stderr)` | console stderr | `Error: ...` configuration diagnostics with exit status 1 | `src/githubtemplateastraluv/config.py`, `src/githubtemplateastraluv/config_render.py` |

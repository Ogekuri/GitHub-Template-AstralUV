# githubtemplateastraluv Runtime Workflow

Runtime model derived from static analysis of `src/` only. Declaration file
paths only; no line numbers. Process IDs are stable.

## Execution Units Index

| ID | Type | Parent process | Role | Entrypoint symbol(s) | Defining file(s) |
| --- | --- | --- | --- | --- | --- |
| `PROC:launcher` | process | none (user shell) | Local-run wrapper resolving the project root, validating `uv`, and delegating to the frozen uv runtime | `scripts/templateastraluv.sh` (bash top-level execution) | `scripts/templateastraluv.sh` |
| `PROC:uv-runtime` | process | `PROC:launcher` | Transient uv process that resolves/creates the project virtual environment and launches the CLI | uv CLI argv: `run --frozen --project <BASE_DIR> python -m githubtemplateastraluv` | `scripts/templateastraluv.sh` |
| `PROC:main` | process | `PROC:uv-runtime` (via launcher) or user interpreter | CLI application process: gated version check plus management-command and configuration-CLI dispatch | `githubtemplateastraluv.__main__:main`; module guard `python -m githubtemplateastraluv` | `src/githubtemplateastraluv/__main__.py`, `src/githubtemplateastraluv/core.py`, `src/githubtemplateastraluv/config.py`, `src/githubtemplateastraluv/config_render.py`, `src/githubtemplateastraluv/colors.py` |
| `PROC:uv-tool-manage` | process | `PROC:main` | Transient child process executing `uv tool upgrade` (PyPI), `uv tool install --reinstall` (develop), `uv tool install` (forced variants), or `uv tool uninstall` (Linux only) | uv CLI argv from `UPGRADE_COMMAND` / `UPGRADE_FORCE_COMMAND` / `UPGRADE_DEVELOP_COMMAND` / `UPGRADE_DEVELOP_FORCE_COMMAND` / `UNINSTALL_COMMAND` | `src/githubtemplateastraluv/management.py` |
| `PROC:build-tooling` | process | none (user shell) | Release-packaging wrapper validating the toolchain, restoring the clean startup state via `scripts/clean.sh`, pruning stale generated artifacts, and delegating the build | `scripts/build.sh` (bash top-level execution) | `scripts/build.sh` |
| `PROC:clean-tooling` | process | `PROC:build-tooling` (delegated) or user shell | Repository cleanup wrapper removing execution-generated caches, bytecode, package metadata, tool caches, build intermediates, the uv virtual environment, and coverage data while preserving `dist/` | `scripts/clean.sh` (bash top-level execution) | `scripts/clean.sh` |
| `PROC:uv-build-runtime` | process | `PROC:build-tooling` | Transient uv process that syncs the locked environment and runs the PEP 517 build backend to produce sdist and wheel into `dist/` | uv CLI argv: `run --frozen --with build python -m build` | `scripts/build.sh` |
| `PROC:release-check` | process | none (user shell) | Release-readiness verifier running fail-fast checks (shell syntax, bytecode compilation, pytest suite, out-of-tree build, artifact validation) with baseline-guarded cleanup and integrity verification | `scripts/pre-release-check.sh` (bash top-level execution) | `scripts/pre-release-check.sh` |
| `PROC:uv-check-runtime` | process | `PROC:release-check` | Transient uv children executing compileall, the pytest suite, the out-of-tree build, and the artifact validator | uv CLI argv: `run python -m compileall -q src tests`, `run pytest`, `run --frozen --with build python -m build --outdir <TMP>`, `run python <validator> <TMP>` | `scripts/pre-release-check.sh` |

Threads: `PROC:main` — no explicit threads detected. `PROC:launcher`,
`PROC:uv-runtime`, `PROC:uv-tool-manage`, `PROC:build-tooling`,
`PROC:clean-tooling`, `PROC:uv-build-runtime`, `PROC:release-check`,
`PROC:uv-check-runtime` — no explicit threads detected.

## Execution Units

### PROC:launcher

- Entrypoint(s): bash interpreter executing `scripts/templateastraluv.sh`
  top-level statements.
- Lifecycle/trigger: starts on user invocation of
  `scripts/templateastraluv.sh`; resolves the absolute script path, derives
  the base and project root directories, rejects execution when the base
  directory differs from the git root, validates `uv` availability
  (non-zero exit with a diagnostic when missing), then replaces itself
  with the uv runtime process via `exec` running the locked environment
  (`--frozen`; or exits non-zero on root-resolution or tool failure).
- Internal Call-Trace Tree: no internal functions under `src/` (linear
  top-level shell script; no function definitions).
- External Boundaries: `readlink -f`, `dirname`, `basename`, `git
  rev-parse --show-toplevel`, `command -v`, `exec` process replacement,
  uv CLI invocation, stderr diagnostics.

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
- Lifecycle/trigger: starts on CLI invocation; runs the gated
  online version check before dispatch unless the configuration
  switch `version_check:disable-version-check` is enabled (REQ-043;
  the dual-source version report variant for `--ver` / `--version`
  always executes, independent of the switch and the gate), prints
  help, prints the aligned
  three-row version report, executes install/uninstall management
  commands with the `--develop` and `--force` upgrade modifiers,
  executes the configuration CLI commands
  (`--get`, `--set`, `--unset`, `--print-raw`, `--print`, `--info`),
  and terminates through `sys.exit` with the dispatcher return code.
- Internal Call-Trace Tree (internal functions only, call order):
  - `main(...)`: disable-switch evaluation, gated check, then command
    dispatch [`src/githubtemplateastraluv/core.py`]
    - `config.version_check_disabled(...)`: tolerant disable-switch
      reader for the automatic check (REQ-042..REQ-044; absent,
      unreadable, malformed, or non-object configuration keeps the
      check enabled) [`src/githubtemplateastraluv/config.py`]
      - `config.load_display(...)`: schema-shaped display-view loader
        [`src/githubtemplateastraluv/config.py`]
        - `config._read_payload(...)`: read and parse the configuration
          JSON document [`src/githubtemplateastraluv/config.py`]
    - `version_check.run_version_check(...)`: online check orchestration
      (skipped when the disable switch is enabled)
      [`src/githubtemplateastraluv/version_check.py`]
      - `colors.notification_colors(...)`: hardcoded ANSI prefixes from
        the embedded internal color JSON
        [`src/githubtemplateastraluv/colors.py`]
      - `version_check._cache_path(...)`: resolve cache file path from
        `$HOME` [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._read_cache(...)`: load idle-time cache JSON
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._gate_allows_request(...)`: idle-time request gate
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._fetch_latest_pypi_version(...)`: HTTPS GET of
        the latest PyPI version
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._parse_version(...)`: tolerant dotted-version
        compare key built from leading-integer components
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._report_failure(...)`: configured-color failure
        note plus 86400 s backoff cache
        [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._print_colored(...)`: ANSI-colored stdout print
          [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._write_cache(...)`: persist four-field cache
          (best effort, REQ-046)
          [`src/githubtemplateastraluv/version_check.py`]
          - `version_check._human_timestamp(...)`: UTC ISO-8601 rendering
            [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._print_colored(...)`: configured-color availability
        note [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._write_cache(...)`: 3600 s refresh cache
        (best effort, REQ-046)
        [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._human_timestamp(...)`
          [`src/githubtemplateastraluv/version_check.py`]
    - `version_check.run_version_report(...)`: forced dual-source version
      report for `--ver` / `--version`; gate, cache-file reads, and the
      disable switch all bypassed (REQ-045)
      [`src/githubtemplateastraluv/version_check.py`]
      - `colors.notification_colors(...)`: hardcoded ANSI prefixes from
        the embedded internal color JSON (same node as under
        `run_version_check`) [`src/githubtemplateastraluv/colors.py`]
      - `version_check._fetch_latest_pypi_version(...)`: HTTPS GET of
        the latest PyPI version
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._fetch_latest_github_version(...)`: HTTPS GET of
        the latest GitHub release tag stripped of its `v` prefix
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._print_colored(...)`: bright red note naming the
        failed source [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._unknown_value(...)`: `unknown (<reason>)`
        placeholder carrying the encountered error for a failed report
        source [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._format_report_row(...)`: label-padded report row
        with aligned version columns
        [`src/githubtemplateastraluv/version_check.py`]
      - `version_check._write_cache(...)`: 3600 s / 86400 s cache driven
        by the PyPI outcome only (best effort, REQ-046)
        [`src/githubtemplateastraluv/version_check.py`]
        - `version_check._human_timestamp(...)`
          [`src/githubtemplateastraluv/version_check.py`]
    - `management.print_help(...)`: print full help screen
      [`src/githubtemplateastraluv/management.py`]
      - `management.build_help_text(...)`: assemble REQ-001/REQ-039 help
        template [`src/githubtemplateastraluv/management.py`]
        - `management._management_entry(...)`: render one aligned command
          line [`src/githubtemplateastraluv/management.py`]
    - `management.cmd_upgrade(...)`: Linux-only upgrade/reinstall via
      `uv tool upgrade` (PyPI), `uv tool install --reinstall` (develop),
      or the forced `--force` variants, with manual-command fallback
      [`src/githubtemplateastraluv/management.py`]
      - `management._upgrade_command(...)`: exact argv selection for the
        requested source/force variant
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
      - `config.load_display(...)`: schema-shaped display-view loader
        tolerating stale-schema persisted content (drops unknown keys,
        default-fills known missing keys)
        [`src/githubtemplateastraluv/config.py`]
        - `config._read_payload(...)`: read and parse the configuration
          JSON document [`src/githubtemplateastraluv/config.py`]
      - `config_render.build_print_root(...)`: build the display node
        tree [`src/githubtemplateastraluv/config_render.py`]
        - `config.resolve_segments(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.section(...)`: public schema section lookup
          [`src/githubtemplateastraluv/config.py`]
        - `config_render.format_table(...)`: measured-width rounded
          box-drawing table with double-line header separator
          [`src/githubtemplateastraluv/config_render.py`]
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
      - `config.load_display(...)`: schema-shaped display-view loader
        tolerating stale-schema persisted content (drops unknown keys,
        default-fills known missing keys)
        [`src/githubtemplateastraluv/config.py`]
        - `config._read_payload(...)`: read and parse the configuration
          JSON document [`src/githubtemplateastraluv/config.py`]
      - `config_render.build_info_root(...)`: build the documentation
        node tree [`src/githubtemplateastraluv/config_render.py`]
        - `config.resolve_segments(...)`
          [`src/githubtemplateastraluv/config.py`]
        - `config.section(...)`: public schema section lookup
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

- Entrypoint(s): `uv tool upgrade githubtemplateastraluv` (PyPI
  upgrade), `uv tool install githubtemplateastraluv --force --reinstall
  --refresh` (forced PyPI source), `uv tool install
  githubtemplateastraluv --reinstall --from
  git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` (develop
  upgrade), `uv tool install githubtemplateastraluv --force --reinstall
  --refresh --from
  git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git` (forced
  develop variant), or `uv tool uninstall githubtemplateastraluv`.
- Lifecycle/trigger: spawned by `PROC:main` only when `is_linux()` is
  true and the user passed `--upgrade` or `--uninstall`; runs to
  completion; its return code propagates to `PROC:main` as the CLI exit
  code.
- Internal Call-Trace Tree: none under `src/` (external tooling process).
- External Boundaries: uv tool environment, PyPI/Git install sources,
  inherited stdio.

### PROC:build-tooling

- Entrypoint(s): bash interpreter executing `scripts/build.sh` top-level
  statements.
- Lifecycle/trigger: starts on user invocation of `scripts/build.sh`;
  resolves the repository root independently of the invocation directory,
  validates the toolchain (`git`, `uv`), restores the canonical
  generated-path startup state by spawning `PROC:clean-tooling`
  (`bash scripts/clean.sh`, non-zero status aborts the build), deletes
  every stale generated first-level `dist/*.tar.gz`, `dist/*.tgz`,
  `dist/*.whl`, and `dist/*.zip` file (any version), then spawns
  `PROC:uv-build-runtime` and blocks until it ends; verifies that
  at least one sdist and one wheel exist in `dist/`, prints the artifact
  summary, and terminates non-zero on toolchain, cleanup, build, or
  verification failure (exit 0 on success). The freshly generated sdist
  and wheel remain in `dist/` as optional release outputs; the cleanup
  delegation guarantees
  that two consecutive builds start from the identical state.
- Internal Call-Trace Tree: no internal functions under `src/` (linear
  top-level shell script; no function definitions).
- External Boundaries: `readlink -f`, `dirname`, `git rev-parse
  --show-toplevel`, `command -v`, `bash scripts/clean.sh` delegation,
  filesystem (`dist/` targeted delete and kept artifacts), uv CLI
  invocation, stdout diagnostics.

### PROC:clean-tooling

- Entrypoint(s): bash interpreter executing `scripts/clean.sh` top-level
  statements (standalone, or delegated by `PROC:build-tooling`).
- Lifecycle/trigger: starts on direct user invocation or on the
  `PROC:build-tooling` delegation after toolchain validation; resolves
  the repository root independently of the invocation directory,
  validates `git`, removes the fixed targets `.pytest_cache/`,
  `.ruff_cache/`, `.mypy_cache/`, `build/`, `.venv/`, the coverage data
  files `.coverage`/`.coverage.*`, and every `__pycache__/` and
  `*.egg-info/` directory at any depth (collected first via a `./dist`
  pruned `find`), logging each handled target; absent targets are a
  successful no-op, any removal failure aborts non-zero, and generated
  release artifacts under `dist/`, tracked files, untracked user files,
  and `$HOME` application data are never touched.
- Internal Call-Trace Tree: no internal functions under `src/` (shell
  function `remove_target` is defined in `scripts/clean.sh`, outside
  `src/`).
- External Boundaries: `readlink -f`, `dirname`, `git rev-parse
  --show-toplevel`, `command -v`, `cd`, `find` (`./dist` pruned
  inventory), `rm -rf`, filesystem removals under the repository root,
  stdout diagnostics.

### PROC:uv-build-runtime

- Entrypoint(s): `uv run --frozen --with build python -m build`.
- Lifecycle/trigger: spawned by `PROC:build-tooling` from the repository
  root; resolves or creates the locked project virtual environment, runs
  the PEP 517 build backend in an isolated build environment to produce
  the sdist and wheel into `dist/`, then exits with the build status.
- Internal Call-Trace Tree: none under `src/` (external tooling process).
- External Boundaries: virtual-environment filesystem, isolated build
  backend environment, PyPI package cache, `dist/` artifacts.

### PROC:release-check

- Entrypoint(s): bash interpreter executing `scripts/pre-release-check.sh`
  top-level statements.
- Lifecycle/trigger: starts on user invocation of
  `scripts/pre-release-check.sh`; resolves the repository root, validates
  the toolchain (`git`, `uv`), allocates a run-scoped temporary work area
  via `mktemp -d`, captures the `git status --porcelain --ignored`
  baseline, then runs the fail-fast phases (tracked-shell syntax `bash -n`
  plus ShellCheck when installed, `python -m compileall` of `src/` and
  `tests/`, `uv run pytest`, out-of-tree `python -m build` into the
  temporary directory, artifact structural validation) by sequentially
  spawning `PROC:uv-check-runtime`; on success, first failure, or trapped
  signal (`SIGINT`/`SIGTERM`/`SIGHUP`), the EXIT trap removes every
  execution-generated repository path (untracked/ignored entries absent
  from the baseline), verifies that the final status equals the baseline,
  removes the temporary work area, and exits with the composed status so
  cleanup never masks the original outcome.
- Internal Call-Trace Tree: no internal functions under `src/` (shell
  functions `run_check`, `run_shell_syntax_checks`, `cleanup_and_verify`,
  `on_exit` are defined in `scripts/pre-release-check.sh`, outside
  `src/`).
- External Boundaries: `readlink -f`, `dirname`, `git rev-parse
  --show-toplevel`, `git status --porcelain --ignored`, `git ls-files`,
  `bash -n`, `shellcheck` (when installed), `command -v`, `mktemp`,
  `cmp`, `diff`, `grep`, `rm -rf`, uv CLI invocations, system temporary
  directory, stdout/stderr diagnostics.

### PROC:uv-check-runtime

- Entrypoint(s): per-phase uv children: `uv run python -m compileall -q
  src tests`, `uv run pytest`, `uv run --frozen --with build python -m
  build --outdir <TMP_BUILD_DIR>`, `uv run python <TMP_VALIDATOR>
  <TMP_BUILD_DIR>`.
- Lifecycle/trigger: spawned sequentially by `PROC:release-check`; each
  child syncs the locked project environment as needed, executes its
  phase, and returns its status; a non-zero status triggers the fail-fast
  abort of `PROC:release-check` (EXIT-trap cleanup still runs).
- Internal Call-Trace Tree: none under `src/` (external tooling
  processes).
- External Boundaries: project virtual environment (`.venv/`), pytest
  suite execution, `compileall` bytecode caches (`__pycache__/`), PEP 517
  build backend isolation, system temporary build output, artifact
  archives under the temporary build directory.

## Communication Edges

| # | Direction | Mechanism | Endpoint / Channel | Payload / Data shape | Declaration file path(s) |
| --- | --- | --- | --- | --- | --- |
| 1 | `PROC:launcher` -> `PROC:uv-runtime` | process `exec` replacement, stdio inherited | uv CLI (`run --frozen --project`) | argv: base directory, `--frozen`, `python -m githubtemplateastraluv`, user arguments | `scripts/templateastraluv.sh` |
| 2 | `PROC:uv-runtime` -> `PROC:main` | child-process spawn, stdio inherited | `python -m githubtemplateastraluv` execution | argv passthrough; CLI exit status returned to uv | `scripts/templateastraluv.sh`, `src/githubtemplateastraluv/__main__.py` |
| 3 | `PROC:main` -> `PROC:uv-tool-manage` | `subprocess.run` spawn, stdio inherited | uv CLI `tool upgrade` / `tool install` / `tool uninstall` | `UPGRADE_COMMAND` / `UPGRADE_FORCE_COMMAND` / `UPGRADE_DEVELOP_COMMAND` / `UPGRADE_DEVELOP_FORCE_COMMAND` / `UNINSTALL_COMMAND` argv; `returncode` propagated | `src/githubtemplateastraluv/management.py` |
| 4 | `PROC:main` -> PyPI (network) | HTTPS GET via `urllib.request.urlopen`, 2 s timeout | `https://pypi.org/pypi/githubtemplateastraluv/json` | JSON object with `info.version` latest published version | `src/githubtemplateastraluv/version_check.py` |
| 5 | `PROC:main` -> GitHub API (network) | HTTPS GET via `urllib.request.urlopen`, 2 s timeout | `https://api.github.com/repos/Ogekuri/GitHub-Template-AstralUV/releases/latest` | JSON object with `tag_name` release tag | `src/githubtemplateastraluv/version_check.py` |
| 6 | `PROC:main` -> filesystem (cache) | JSON file read/write with parent-directory creation (best-effort write, REQ-046) | `$HOME/.cache/githubtemplateastraluv/check_version_idle-time.json` | four-field JSON: `last_check_epoch`, `last_check_human`, `idle_time_epoch`, `idle_time_human` | `src/githubtemplateastraluv/version_check.py` |
| 7 | `PROC:main` -> stdout | `print()` (optionally ANSI SGR configured colors, default bright green 92 / bright red 91) | console stdout | help screen text, three-row aligned version report, availability/error notifications, configuration JSON (`--get`), configuration trees (`--print`/`--info`), raw file bytes (`--print-raw`) | `src/githubtemplateastraluv/core.py`, `src/githubtemplateastraluv/management.py`, `src/githubtemplateastraluv/version_check.py`, `src/githubtemplateastraluv/config.py`, `src/githubtemplateastraluv/config_render.py` |
| 8 | `PROC:launcher` -> stderr | shell `echo` diagnostics | console stderr | project-root resolution errors | `scripts/templateastraluv.sh` |
| 9 | `PROC:main` -> filesystem (configuration) | JSON file read/write with parent-directory creation, temporary-file fsync, and `os.replace` atomic swap | `$HOME/.config/githubtemplateastraluv/config.json` | validated schema JSON object (`version_check` section with the `disable-version-check` switch; also read tolerantly at startup before dispatch); raw bytes for `--print-raw` | `src/githubtemplateastraluv/config.py` |
| 10 | `PROC:main` -> stderr | `print(..., file=sys.stderr)` | console stderr | `Error: ...` configuration diagnostics with exit status 1 | `src/githubtemplateastraluv/config.py`, `src/githubtemplateastraluv/config_render.py` |
| 11 | `PROC:build-tooling` -> `PROC:uv-build-runtime` | child-process spawn, stdio inherited | uv CLI `run --frozen --with build python -m build` | argv with repository-root cwd; generated sdist/wheel in `dist/`; `returncode` propagated | `scripts/build.sh` |
| 12 | `PROC:build-tooling` -> filesystem (dist/) | targeted file delete plus build-backend writes | `<repo root>/dist/` | stale `*.tar.gz`/`*.tgz`/`*.whl`/`*.zip` removal before build; fresh sdist and wheel preserved after build | `scripts/build.sh` |
| 13 | `PROC:build-tooling` -> `PROC:clean-tooling` | child-process spawn (`bash scripts/clean.sh`), stdio inherited | pre-build repository cleanup | cleanup log lines on stdout; `returncode` gates the build (non-zero aborts) | `scripts/build.sh` |
| 14 | `PROC:clean-tooling` -> filesystem (generated paths) | `rm -rf` removals of an inventory collected by a `./dist`-pruned `find` | `<repo root>/` | `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `build/`, `.venv/`, `.coverage`/`.coverage.*`, `__pycache__/`, `*.egg-info/` removed; `dist/` and user content preserved | `scripts/clean.sh` |
| 15 | `PROC:release-check` -> `PROC:uv-check-runtime` | sequential child-process spawn, stdio inherited | uv CLI `run` (compileall / pytest / out-of-tree build / artifact validator) | phase argv; `returncode` drives the fail-fast abort | `scripts/pre-release-check.sh` |
| 16 | `PROC:release-check` -> filesystem (system temp) | `mktemp -d` allocation, file writes, recursive removal | system temporary work directory | git-status baseline/current/final snapshots, out-of-tree build output, artifact validator script | `scripts/pre-release-check.sh` |
| 17 | `PROC:release-check` -> filesystem (repository generated paths) | creation via test/build tooling, then baseline-diff `rm -rf` removal | `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/` under the repository | execution-generated caches and environments removed on success, failure, or signal; pre-existing content preserved | `scripts/pre-release-check.sh` |

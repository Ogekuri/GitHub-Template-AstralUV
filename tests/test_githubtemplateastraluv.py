#!/usr/bin/env python3
## @file test_githubtemplateastraluv.py
# @brief HDT unit suite (Generator mode) covering TST-001..TST-032 for
#        the githubtemplateastraluv CLI, its release workflow, its
#        repository tooling scripts, and its packaging-artifact contract.
# @details HDT static-analysis artifact (section 7.1):
#          - UUTs and levels: L0 = management.is_linux,
#            management._management_entry, version_check._parse_version,
#            version_check._human_timestamp,
#            version_check._format_report_row, config.section,
#            colors.notification_colors; L1 =
#            management.build_help_text, management.print_help,
#            management.cmd_upgrade, management.cmd_uninstall,
#            version_check._read_cache, version_check._write_cache,
#            version_check._gate_allows_request,
#            version_check._fetch_latest_pypi_version,
#            version_check._fetch_latest_github_version,
#            version_check.run_version_check,
#            version_check.run_version_report; L2 = core.main.
#          - External dependencies isolated: network (urlopen mocked),
#            filesystem ($HOME redirected into tmp_path), process spawn
#            (subprocess.run mocked), wall clock (tolerance-bounded
#            assertions on the 3600/86400 second deltas).
#          - Stale-schema rendering reproducer: `--print` and `--info`
#            render the schema-shaped tree from a configuration file
#            persisted by an older schema version (DES-010, TST-008;
#            REQ-019, REQ-023).
#          - Contract checks (TST-012..TST-015): action pins and job
#            topology of `.github/workflows/release-pypi.yml` versus the
#            Node24-or-later manifest (DES-015, CTN-010) plus the PyPI
#            trusted-publisher contract (DES-016, DES-017, DES-018); the
#            tracked workflow file is the read-only deterministic fixture.
#          - Packaging-artifact contract: embedded `Version`/`Classifier`
#            core metadata of the tracked `dist/` sdist and wheel versus
#            `pyproject.toml` (DES-016, DES-017, DES-042); the tracked
#            artifacts are the read-only deterministic fixtures.
#          - Release-tooling sandbox contracts (TST-016..TST-018,
#            TST-029): `scripts/build.sh`, `scripts/pre-release-check.sh`,
#            and `scripts/templateastraluv.sh` execute inside disposable
#            git sandboxes under tmp_path; uv provisions the build
#            tooling from the local uv cache; `VIRTUAL_ENV` is stripped
#            from the child environments.
#          - Execution plan (dev signal): `uv run pytest` from the project
#            root; CI gates L0 -> L1 -> L2 fail-fast outside test bodies.
import email.message
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time
import tomllib
import urllib.error
from unittest import mock
import zipfile

import pytest

import githubtemplateastraluv.colors as colors
import githubtemplateastraluv.config as config
import githubtemplateastraluv.config_render as config_render
import githubtemplateastraluv.core as core
import githubtemplateastraluv.management as management
import githubtemplateastraluv.version_check as version_check

## @brief PyPI endpoint oracle duplicated from the SRS (REQ-009, REQ-028)
#         to keep assertions independent from implementation constants.
EXPECTED_PYPI_ENDPOINT = (
    "https://pypi.org/pypi/githubtemplateastraluv/json"
)

## @brief GitHub endpoint oracle duplicated from the SRS (REQ-029).
EXPECTED_GITHUB_ENDPOINT = (
    "https://api.github.com/repos/Ogekuri/"
    "GitHub-Template-AstralUV/releases/latest"
)

## @brief Independent byte-exact help-screen oracle for TST-001 (REQ-001
#         template with the current version substituted into the `(x.y.z)`
#         slot; single version source `core.__version__`).
EXPECTED_HELP_TEXT = (
    "Usage: githubtemplateastraluv [command] [options] "
    f"({core.__version__})\n"
    "\n"
    "Management Commands:\n"
    "  --upgrade   - Reinstall githubtemplateastraluv on Linux; print manual"
    " command elsewhere.\n"
    "  --uninstall - Uninstall githubtemplateastraluv on Linux; print manual"
    " command elsewhere.\n"
    "  --ver       - Print the githubtemplateastraluv version.\n"
    "  --version   - Print the githubtemplateastraluv version.\n"
    "  --help      - Print the full help screen.\n"
    "\n"
    "Configuration Commands:\n"
    "  --get       - Print the value at Path as one JSON document.\n"
    "  --set       - Parse Value into the schema type and persist it at"
    " Path.\n"
    "  --unset     - Restore Path to its schema default and persist"
    " atomically.\n"
    "  --print     - Print current values as a box-drawing tree, whole"
    " schema or at Path.\n"
    "  --info      - Print parameter documentation with defaults,"
    " constraints, and examples.\n"
    "  --print-raw - Print the exact bytes of the configuration JSON file.\n"
    "\n"
    "Options:\n"
    "  --develop   - With --upgrade: install from the GitHub development"
    " source.\n"
    "  --force     - With --upgrade: force full re-download and"
    " reinstallation."
)


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """@brief Redirect `$HOME` into a per-test temp directory.

    @details HDT isolation: version-check cache writes never touch the
             real user filesystem.
    @return {Path} The isolated home directory.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


def _cache_file(home):
    """@brief Resolve the cache file path inside an isolated home.

    @param home {Path} Isolated home directory.
    @return {Path} Cache file path `home/.cache/githubtemplateastraluv/
            check_version_idle-time.json`.
    """
    return (
        home
        / ".cache"
        / "githubtemplateastraluv"
        / "check_version_idle-time.json"
    )


def _write_cache(home, idle_epoch):
    """@brief Seed an idle-time cache holding a four-field payload.

    @param home {Path} Isolated home directory.
    @param idle_epoch {float} `idle_time_epoch` value to persist.
    @return {None}
    """
    path = _cache_file(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_check_epoch": int(idle_epoch) - 3600,
        "last_check_human": "1970-01-01T00:00:00Z",
        "idle_time_epoch": int(idle_epoch),
        "idle_time_human": "1970-01-01T00:00:00Z",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_config(home, payload_text):
    """@brief Seed the global configuration file inside an isolated home.

    @param home {Path} Isolated home directory.
    @param payload_text {str} Exact JSON text to persist.
    @return {Path} Configuration file path `home/.config/
            githubtemplateastraluv/config.json`.
    """
    path = home / ".config" / "githubtemplateastraluv" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload_text, encoding="utf-8")
    return path


def _mock_urlopen(payload):
    """@brief Build a patched `urlopen` returning one static payload.

    @param payload {dict} JSON payload returned for every request.
    @return {mock.MagicMock} Context-manager stand-in for urlopen.
    """
    urlopen = mock.MagicMock()
    response = urlopen.return_value.__enter__.return_value
    response.read.return_value = json.dumps(payload).encode("utf-8")
    return urlopen


def _mock_urlopen_by_url(payloads):
    """@brief Build a patched `urlopen` dispatching payloads by URL.

    @details Each call returns a context-manager response whose `read`
             emits the JSON payload mapped to the request URL; unknown
             URLs raise KeyError.
    @param payloads {dict[str, dict]} Mapping endpoint URL -> JSON payload.
    @return {mock.MagicMock} urlopen stand-in recording all calls.
    """

    def _respond(request, timeout):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            payloads[request.get_full_url()]
        ).encode("utf-8")
        return response

    urlopen = mock.MagicMock()
    urlopen.side_effect = _respond
    return urlopen


def test_no_args_prints_exact_help_and_runs_gated_check(
    isolated_home, capsys
):
    """@brief TST-001 no-args branch: exact help screen, gated check first.

    @details expected_output = EXPECTED_HELP_TEXT plus trailing newline;
            expected_exception = none.
    """
    with mock.patch.object(
        version_check, "run_version_check"
    ) as check_mock:
        with mock.patch.object(
            version_check.urllib.request, "urlopen"
        ) as urlopen_mock:
            exit_code = core.main([])
    assert exit_code == 0
    assert capsys.readouterr().out == EXPECTED_HELP_TEXT + "\n"
    check_mock.assert_called_once_with(core.__version__, False)
    urlopen_mock.assert_not_called()


def test_help_flag_prints_exact_help(isolated_home, capsys):
    """@brief TST-001 `--help` branch: exact help screen on stdout.

    @details expected_output = EXPECTED_HELP_TEXT plus trailing newline;
            expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        exit_code = core.main(["--help"])
    assert exit_code == 0
    assert capsys.readouterr().out == EXPECTED_HELP_TEXT + "\n"


def test_ver_report_prints_aligned_rows_despite_fresh_cache(
    isolated_home, capsys
):
    """@brief TST-002/TST-013: forced report bypasses the cache gate.

    @details expected_output = the exact three aligned rows (REQ-027) with
            mocked PyPI and GitHub payloads; both fetches run even with an
            unexpired cache file; cache refreshed 3600 s (REQ-031);
            expected_exception = none.
    """
    _write_cache(isolated_home, time.time() + 9999)
    urlopen_mock = _mock_urlopen_by_url(
        {
            EXPECTED_PYPI_ENDPOINT: {"info": {"version": "9.9.9"}},
            EXPECTED_GITHUB_ENDPOINT: {"tag_name": "v8.8.8"},
        }
    )
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        exit_code = core.main(["--ver"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert out == (
        f"Current Installed : {core.__version__}\n"
        "Latest @ PyPI     : 9.9.9\n"
        "Latest @ GitHub   : 8.8.8\n"
    )
    assert urlopen_mock.call_count == 2
    _assert_cache_fields(isolated_home, 3600)


def test_disable_version_check_yes_skips_gated_check(
    isolated_home, capsys
):
    """@brief TST-025: the disable switch suppresses the gated check.

    @details UUT: core.main (L1 composed). expected_output = exit 0, the
            exact help screen on stdout, zero urlopen calls, no cache
            file, and no run_version_check execution with
            `version_check:disable-version-check = yes` (REQ-042,
            REQ-043); expected_exception = none.
    """
    _write_config(
        isolated_home,
        '{"version_check": {"disable-version-check": "yes"}}\n',
    )
    assert config.version_check_disabled() is True
    with mock.patch.object(
        version_check, "run_version_check"
    ) as check_mock:
        with mock.patch.object(
            version_check.urllib.request, "urlopen"
        ) as urlopen_mock:
            exit_code = core.main([])
    assert exit_code == 0
    assert capsys.readouterr().out == EXPECTED_HELP_TEXT + "\n"
    check_mock.assert_not_called()
    urlopen_mock.assert_not_called()
    assert not _cache_file(isolated_home).exists()


def test_disable_version_check_absent_or_malformed_keeps_check_enabled(
    isolated_home,
):
    """@brief TST-025/REQ-044: tolerant default keeps the check enabled.

    @details UUTs: core.main, config.version_check_disabled (L1
            composed). expected_output = run_version_check executed once
            per case (absent, malformed-JSON, non-object configuration)
            and version_check_disabled() False in every case
            (REQ-044); expected_exception = none.
    """
    with mock.patch.object(
        version_check, "run_version_check"
    ) as check_mock:
        exit_code = core.main([])
    assert exit_code == 0
    check_mock.assert_called_once_with(core.__version__, False)
    assert config.version_check_disabled() is False

    for broken_payload in ("{not json", "[]"):
        _write_config(isolated_home, broken_payload)
        with mock.patch.object(
            version_check, "run_version_check"
        ) as check_mock:
            core.main([])
        check_mock.assert_called_once_with(core.__version__, False)
        assert config.version_check_disabled() is False


def test_ver_report_active_when_version_check_disabled(
    isolated_home, capsys
):
    """@brief TST-026/REQ-045: --ver stays active with the switch enabled.

    @details UUT: core.main (L1 composed). expected_output = exit 0, the
            exact three aligned rows (REQ-027) with mocked PyPI and
            GitHub payloads, both fetches executed, and the cache
            refreshed 3600 s (REQ-031) even with
            `version_check:disable-version-check = yes`;
            expected_exception = none.
    """
    _write_config(
        isolated_home,
        '{"version_check": {"disable-version-check": "yes"}}\n',
    )
    urlopen_mock = _mock_urlopen_by_url(
        {
            EXPECTED_PYPI_ENDPOINT: {"info": {"version": "9.9.9"}},
            EXPECTED_GITHUB_ENDPOINT: {"tag_name": "v8.8.8"},
        }
    )
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        exit_code = core.main(["--ver"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert out == (
        f"Current Installed : {core.__version__}\n"
        "Latest @ PyPI     : 9.9.9\n"
        "Latest @ GitHub   : 8.8.8\n"
    )
    assert urlopen_mock.call_count == 2
    _assert_cache_fields(isolated_home, 3600)


def test_upgrade_on_linux_executes_exact_uv_install(isolated_home):
    """@brief TST-003: `--upgrade` spawns the exact REQ-003 argv on Linux.

    @details expected_output = exit code 0, one subprocess.run call with
            UPGRADE_COMMAND, and UPGRADE_COMMAND equal to the literal
            REQ-003 string `uv tool upgrade githubtemplateastraluv`;
            expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=True):
            with mock.patch.object(
                management.subprocess,
                "run",
                return_value=mock.Mock(returncode=0),
            ) as run_mock:
                exit_code = core.main(["--upgrade"])
    assert exit_code == 0
    assert management.UPGRADE_COMMAND == [
        "uv",
        "tool",
        "upgrade",
        "githubtemplateastraluv",
    ]
    run_mock.assert_called_once_with(management.UPGRADE_COMMAND, check=False)


def test_upgrade_develop_on_linux_executes_exact_uv_install(isolated_home):
    """@brief TST-014 (REQ-032): `--upgrade --develop` spawns exact argv.

    @details expected_output = exit code 0, one subprocess.run call with
            UPGRADE_DEVELOP_COMMAND, and UPGRADE_DEVELOP_COMMAND equal to
            the literal REQ-032 reinstall-from-git string;
            expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=True):
            with mock.patch.object(
                management.subprocess,
                "run",
                return_value=mock.Mock(returncode=0),
            ) as run_mock:
                exit_code = core.main(["--upgrade", "--develop"])
    assert exit_code == 0
    assert management.UPGRADE_DEVELOP_COMMAND == [
        "uv",
        "tool",
        "install",
        "githubtemplateastraluv",
        "--reinstall",
        "--from",
        "git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git@develop",
    ]
    run_mock.assert_called_once_with(
        management.UPGRADE_DEVELOP_COMMAND, check=False
    )


def test_upgrade_force_on_linux_executes_exact_uv_install(isolated_home):
    """@brief TST-003 (REQ-035): `--upgrade --force` spawns exact argv.

    @details expected_output = exit code 0 and one subprocess.run call with
            UPGRADE_FORCE_COMMAND; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=True):
            with mock.patch.object(
                management.subprocess,
                "run",
                return_value=mock.Mock(returncode=0),
            ) as run_mock:
                exit_code = core.main(["--upgrade", "--force"])
    assert exit_code == 0
    run_mock.assert_called_once_with(
        management.UPGRADE_FORCE_COMMAND, check=False
    )


def test_upgrade_develop_force_on_linux_executes_exact_uv_install(
    isolated_home,
):
    """@brief TST-003/TST-014 (REQ-036): forced develop argv executes.

    @details expected_output = exit code 0 and one subprocess.run call with
            UPGRADE_DEVELOP_FORCE_COMMAND; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=True):
            with mock.patch.object(
                management.subprocess,
                "run",
                return_value=mock.Mock(returncode=0),
            ) as run_mock:
                exit_code = core.main(
                    ["--upgrade", "--develop", "--force"]
                )
    assert exit_code == 0
    run_mock.assert_called_once_with(
        management.UPGRADE_DEVELOP_FORCE_COMMAND, check=False
    )


def test_uninstall_on_linux_executes_exact_uv_uninstall(isolated_home):
    """@brief TST-003: `--uninstall` spawns the exact REQ-005 argv on Linux.

    @details expected_output = exit code 0 and one subprocess.run call with
            UNINSTALL_COMMAND; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=True):
            with mock.patch.object(
                management.subprocess,
                "run",
                return_value=mock.Mock(returncode=0),
            ) as run_mock:
                exit_code = core.main(["--uninstall"])
    assert exit_code == 0
    run_mock.assert_called_once_with(
        management.UNINSTALL_COMMAND, check=False
    )


def test_upgrade_on_non_linux_prints_manual_without_execution(
    isolated_home, capsys
):
    """@brief TST-004: non-Linux `--upgrade` prints warning, spawns nothing.

    @details expected_output = warning plus the REQ-003 manual command on
            stdout and zero subprocess spawns; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=False):
            with mock.patch.object(
                management.subprocess, "run"
            ) as run_mock:
                exit_code = core.main(["--upgrade"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "WARNING" in out
    assert " ".join(management.UPGRADE_COMMAND) in out
    run_mock.assert_not_called()


def test_upgrade_develop_on_non_linux_prints_manual_without_execution(
    isolated_home, capsys
):
    """@brief TST-014 (REQ-033): non-Linux develop upgrade prints manual.

    @details expected_output = warning plus the REQ-032 manual command on
            stdout and zero subprocess spawns; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=False):
            with mock.patch.object(
                management.subprocess, "run"
            ) as run_mock:
                exit_code = core.main(["--upgrade", "--develop"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "WARNING" in out
    assert " ".join(management.UPGRADE_DEVELOP_COMMAND) in out
    run_mock.assert_not_called()


def test_upgrade_force_on_non_linux_prints_manual_without_execution(
    isolated_home, capsys
):
    """@brief TST-004 (REQ-004/REQ-035): non-Linux forced upgrade manual.

    @details expected_output = warning plus the REQ-035 manual command on
            stdout and zero subprocess spawns; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=False):
            with mock.patch.object(
                management.subprocess, "run"
            ) as run_mock:
                exit_code = core.main(["--upgrade", "--force"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "WARNING" in out
    assert " ".join(management.UPGRADE_FORCE_COMMAND) in out
    run_mock.assert_not_called()


def test_upgrade_develop_force_on_non_linux_prints_manual_without_execution(
    isolated_home, capsys
):
    """@brief TST-004/TST-014 (REQ-033/REQ-036): forced develop manual.

    @details expected_output = warning plus the REQ-036 manual command on
            stdout and zero subprocess spawns; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=False):
            with mock.patch.object(
                management.subprocess, "run"
            ) as run_mock:
                exit_code = core.main(
                    ["--upgrade", "--develop", "--force"]
                )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "WARNING" in out
    assert " ".join(management.UPGRADE_DEVELOP_FORCE_COMMAND) in out
    run_mock.assert_not_called()


def test_develop_alone_falls_back_to_help_without_upgrade(
    isolated_home, capsys
):
    """@brief TST-014 (REQ-034): `--develop` alone dispatches no upgrade.

    @details expected_output = exact help screen and zero subprocess
            spawns; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=True):
            with mock.patch.object(
                management.subprocess, "run"
            ) as run_mock:
                exit_code = core.main(["--develop"])
    assert exit_code == 0
    assert capsys.readouterr().out == EXPECTED_HELP_TEXT + "\n"
    run_mock.assert_not_called()


def test_force_alone_falls_back_to_help_without_upgrade(
    isolated_home, capsys
):
    """@brief TST-014 (REQ-038): `--force` alone dispatches no upgrade.

    @details expected_output = exact help screen and zero subprocess
            spawns; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=True):
            with mock.patch.object(
                management.subprocess, "run"
            ) as run_mock:
                exit_code = core.main(["--force"])
    assert exit_code == 0
    assert capsys.readouterr().out == EXPECTED_HELP_TEXT + "\n"
    run_mock.assert_not_called()


def test_uninstall_on_non_linux_prints_manual_without_execution(
    isolated_home, capsys
):
    """@brief TST-004: non-Linux `--uninstall` prints warning, spawns none.

    @details expected_output = warning plus the REQ-005 manual command on
            stdout and zero subprocess spawns; expected_exception = none.
    """
    with mock.patch.object(version_check, "run_version_check"):
        with mock.patch.object(management, "is_linux", return_value=False):
            with mock.patch.object(
                management.subprocess, "run"
            ) as run_mock:
                exit_code = core.main(["--uninstall"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "WARNING" in out
    assert " ".join(management.UNINSTALL_COMMAND) in out
    run_mock.assert_not_called()


def test_absent_cache_triggers_request_with_two_second_timeout(
    isolated_home, capsys
):
    """@brief TST-005: cache-miss -> one request, timeout 2, PyPI endpoint.

    @details expected_output = bright-green note for the newer 9.9.9
            version; request URL equals EXPECTED_PYPI_ENDPOINT and timeout
            equals 2 (REQ-009, REQ-028).
    """
    urlopen_mock = _mock_urlopen({"info": {"version": "9.9.9"}})
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        version_check.run_version_check("0.0.0")
    urlopen_mock.assert_called_once()
    request = urlopen_mock.call_args[0][0]
    assert request.get_full_url() == EXPECTED_PYPI_ENDPOINT
    assert urlopen_mock.call_args.kwargs["timeout"] == 2
    out = capsys.readouterr().out
    assert "\033[92m" in out
    assert "9.9.9" in out


def test_unexpired_cache_skips_request(isolated_home, capsys):
    """@brief TST-005: gate closed -> zero requests, zero output.

    @details expected_output = empty stdout and no urlopen invocation;
            expected_exception = none.
    """
    _write_cache(isolated_home, time.time() + 9999)
    with mock.patch.object(
        version_check.urllib.request, "urlopen"
    ) as urlopen_mock:
        version_check.run_version_check("0.0.0")
    urlopen_mock.assert_not_called()
    assert capsys.readouterr().out == ""


def test_expired_cache_triggers_request(isolated_home):
    """@brief TST-005 boundary: elapsed idle-time reopens the gate.

    @details expected_output = exactly one urlopen invocation; expected
            exception = none.
    """
    _write_cache(isolated_home, time.time() - 10)
    urlopen_mock = _mock_urlopen({"info": {"version": "0.0.1"}})
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        version_check.run_version_check("0.0.0")
    urlopen_mock.assert_called_once()


def _assert_cache_fields(home, expected_delay):
    """@brief Assert the four-field cache shape and idle-time delta.

    @param home {Path} Isolated home directory.
    @param expected_delay {int} Expected idle-delay delta (3600/86400).
    @return {None}
    """
    cache = json.loads(
        _cache_file(home).read_text(encoding="utf-8")
    )
    assert set(cache) == {
        "last_check_epoch",
        "last_check_human",
        "idle_time_epoch",
        "idle_time_human",
    }
    assert cache["idle_time_epoch"] == pytest.approx(
        time.time() + expected_delay, abs=10
    )
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", cache["idle_time_human"]
    )


def test_newer_release_prints_green_and_writes_cache_3600(
    isolated_home, capsys
):
    """@brief TST-006: newer release -> bright green note, 3600 s cache.

    @details expected_output = bright-green message comparing available and
            installed versions; cache holds four fields with idle-time
            equal to check time plus 3600; expected_exception = none.
    """
    urlopen_mock = _mock_urlopen({"info": {"version": "9.9.9"}})
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        version_check.run_version_check("0.0.0")
    out = capsys.readouterr().out
    assert "\033[92m" in out
    assert "New version available: 9.9.9" in out
    assert "(installed version: 0.0.0)" in out
    _assert_cache_fields(isolated_home, 3600)


def test_equal_release_no_notification_but_cache_refreshed(
    isolated_home, capsys
):
    """@brief TST-006 boundary (A-04): up-to-date -> silent, cache + 3600.

    @details expected_output = empty stdout; cache refreshed with the
            standard idle-delay; expected_exception = none.
    """
    urlopen_mock = _mock_urlopen({"info": {"version": "0.0.0"}})
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        version_check.run_version_check("0.0.0")
    assert capsys.readouterr().out == ""
    _assert_cache_fields(isolated_home, 3600)


def test_http_503_prints_red_and_backs_off_86400(isolated_home, capsys):
    """@brief TST-007: HTTP 503 -> bright red note, 86400 s backoff cache.

    @details expected_output = bright-red message carrying the 503 error;
            cache idle-time equals attempt time plus 86400; expected
            exception = none (handled internally).
    """
    headers = email.message.Message()
    http_error = urllib.error.HTTPError(
        EXPECTED_PYPI_ENDPOINT, 503, "Service Unavailable", headers, None
    )
    with mock.patch.object(
        version_check.urllib.request,
        "urlopen",
        mock.Mock(side_effect=http_error),
    ):
        version_check.run_version_check("0.0.0")
    out = capsys.readouterr().out
    assert "\033[91m" in out
    assert "503" in out
    _assert_cache_fields(isolated_home, 86400)


def test_timeout_failure_prints_red_and_backs_off_86400(
    isolated_home, capsys
):
    """@brief TST-007 error path: TimeoutError -> red note, 86400 backoff.

    @details expected_output = bright-red message carrying the timeout
            error; cache idle-time equals attempt time plus 86400.
    """
    with mock.patch.object(
        version_check.urllib.request,
        "urlopen",
        mock.Mock(side_effect=TimeoutError("timed out")),
    ):
        version_check.run_version_check("0.0.0")
    out = capsys.readouterr().out
    assert "\033[91m" in out
    assert "timed out" in out
    _assert_cache_fields(isolated_home, 86400)


def test_ver_report_marks_failed_pypi_source_unknown(
    isolated_home, capsys
):
    """@brief TST-013 (REQ-030/REQ-031): failed PyPI -> unknown row.

    @details expected_output = `unknown (HTTP Error 503: Service
            Unavailable)` in the PyPI row (REQ-030 reason rendering),
            populated GitHub row, bright red note naming PyPI; cache backs
            off 86400 s (PyPI outcome only); expected_exception = none
            (handled internally).
    """

    def _respond(request, timeout):
        if request.get_full_url() == EXPECTED_PYPI_ENDPOINT:
            raise urllib.error.HTTPError(
                EXPECTED_PYPI_ENDPOINT,
                503,
                "Service Unavailable",
                email.message.Message(),
                None,
            )
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"tag_name": "v8.8.8"}
        ).encode("utf-8")
        return response

    urlopen_mock = mock.MagicMock()
    urlopen_mock.side_effect = _respond
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        exit_code = core.main(["--ver"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert (
        "Latest @ PyPI     : unknown (HTTP Error 503: Service"
        " Unavailable)\n" in out
    )
    assert "Latest @ GitHub   : 8.8.8\n" in out
    assert "\033[91m" in out
    assert "@ PyPI" in out
    _assert_cache_fields(isolated_home, 86400)


def test_ver_report_marks_failed_github_source_unknown(
    isolated_home, capsys
):
    """@brief TST-013 (REQ-030/REQ-031): failed GitHub -> unknown row.

    @details expected_output = populated PyPI row, `unknown (timed out)`
            in the GitHub row (REQ-030 reason rendering), bright red note
            naming GitHub; cache refreshed 3600 s (PyPI outcome only);
            expected_exception = none (handled internally).
    """

    def _respond(request, timeout):
        if request.get_full_url() == EXPECTED_GITHUB_ENDPOINT:
            raise TimeoutError("timed out")
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"info": {"version": "9.9.9"}}
        ).encode("utf-8")
        return response

    urlopen_mock = mock.MagicMock()
    urlopen_mock.side_effect = _respond
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        exit_code = core.main(["--ver"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Latest @ PyPI     : 9.9.9\n" in out
    assert "Latest @ GitHub   : unknown (timed out)\n" in out
    assert "\033[91m" in out
    assert "@ GitHub" in out
    _assert_cache_fields(isolated_home, 3600)


## @brief Release workflow contract file exercised by TST-012 and
#         TST-015; its file name matches the pending PyPI trusted
#         publisher (DES-016).
RELEASE_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "release-pypi.yml"
)

## @brief Minimum major version per workflow action whose runtime is
#         Node24 or later (DES-015).
# @details `pypa/gh-action-pypi-publish` is a Docker action and declares
#          no JavaScript runtime; its entry keeps the manifest exhaustive
#          over every `uses:` pin of the release workflow.
NODE24_ACTION_MIN_MAJOR = {
    "actions/checkout": 5,
    "actions/attest-build-provenance": 4,
    "mikepenz/release-changelog-builder-action": 6,
    "softprops/action-gh-release": 3,
    "pypa/gh-action-pypi-publish": 1,
}

## @brief Node20 back-compat environment variables forbidden by CTN-010.
NODE20_FALLBACK_VARIABLES = (
    "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24",
    "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION",
)


def _release_workflow_pins():
    """@brief Extract every `uses:` pin from the release workflow.

    @details Reads `RELEASE_WORKFLOW_PATH` and applies the line pattern
            `uses:` plus one non-space token; returns pin tokens in
            declaration order. Complexity: O(L) over file lines L.
    @return {list[str]} Pin tokens in `owner/repo@version` form.
    """
    pattern = re.compile(r"\buses:\s*(\S+)")
    pins = []
    for line in RELEASE_WORKFLOW_PATH.read_text(
        encoding="utf-8"
    ).splitlines():
        match = pattern.search(line)
        if match:
            pins.append(match.group(1))
    return pins


@pytest.mark.parametrize(
    "pin", _release_workflow_pins(), ids=lambda pin: pin
)
def test_release_workflow_pin_is_node24_or_later(pin):
    """@brief TST-012 (DES-015): one pin satisfies the Node24 manifest.

    @details expected_output = none; expected_exception = AssertionError
            when the pin action is unlisted or its major version is below
            the Node24-or-later minimum major.
    @param pin {str} Workflow pin token `owner/repo@version`.
    """
    action, _, version = pin.partition("@")
    assert action in NODE24_ACTION_MIN_MAJOR, pin
    if version.startswith("release/"):
        version = version[len("release/"):]
    assert version.startswith("v"), pin
    major = int(version[1:].split(".")[0])
    assert major >= NODE24_ACTION_MIN_MAJOR[action], pin


def test_release_workflow_declares_node24_release_stack():
    """@brief TST-012 boundary: golden pin oracle for the migrated stack.

    @details expected_output = none; expected_exception = AssertionError
            when the declaration-order pin list differs from the
            build-free Node24 stack (three checkout pins,
            attest-build-provenance, changelog builder, gh-release, PyPI
            publisher).
    """
    assert _release_workflow_pins() == [
        "actions/checkout@v5",
        "actions/checkout@v5",
        "actions/attest-build-provenance@v4",
        "mikepenz/release-changelog-builder-action@v6",
        "softprops/action-gh-release@v3",
        "actions/checkout@v5",
        "pypa/gh-action-pypi-publish@release/v1",
    ]


def test_release_workflow_has_no_node20_fallback_variables():
    """@brief TST-012 (CTN-010): Node20 opt-out variables stay unset.

    @details expected_output = none; expected_exception = AssertionError
            when any forbidden Node20 fallback or forced-runtime variable
            name occurs in the workflow text.
    """
    workflow_text = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")
    for variable in NODE20_FALLBACK_VARIABLES:
        assert variable not in workflow_text, variable


def _workflow_job_block(name):
    """@brief Extract one top-level job block from the release workflow.

    @details Returns the lines from the two-space-indented `  <name>:`
             header until the next job header (same indentation, `key:`
             form) or end of file. Complexity: O(L) over file lines L.
    @param name {str} YAML job key (e.g. `publish-pypi`).
    @return {str} Job block text including the header line.
    @throws {ValueError} If the header line is absent.
    """
    lines = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8").splitlines()
    header = f"  {name}:"
    start = lines.index(header)
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if re.fullmatch(r"  [A-Za-z0-9_-]+:", lines[index]):
            end = index
            break
    return "\n".join(lines[start:end])


def test_release_workflow_file_matches_trusted_publisher_contract():
    """@brief TST-015 (DES-016): workflow file name matches the publisher.

    @details expected_output = none; expected_exception = AssertionError
            when the tracked workflow file is not `release-pypi.yml` or
            the legacy `release-uvx.yml` still exists.
    """
    assert RELEASE_WORKFLOW_PATH.name == "release-pypi.yml"
    workflows_dir = RELEASE_WORKFLOW_PATH.parent
    assert not (workflows_dir / "release-uvx.yml").exists()


def test_release_workflow_publish_job_is_oidc_master_only():
    """@brief TST-015 (DES-017): OIDC publish job gated on master tags.

    @details expected_output = none; expected_exception = AssertionError
            when the publish job lacks the master gate, the id-token
            permission, the tag checkout, or the PyPI trusted-publishing
            action pin.
    """
    block = _workflow_job_block("publish-pypi")
    assert "needs: [check-branch, release]" in block
    assert "needs.check-branch.outputs.is_master == 'true'" in block
    assert "id-token: write" in block
    assert "actions/checkout" in block
    assert "pypa/gh-action-pypi-publish@release/v1" in block


def test_release_workflow_release_job_runs_for_every_tag():
    """@brief TST-015 (DES-018): release job runs for every canonical tag.

    @details expected_output = none; expected_exception = AssertionError
            when the release job carries a branch gate, misses the tag
            checkout or the GitHub release step, or still builds.
    """
    block = _workflow_job_block("release")
    assert "is_master" not in block
    assert not re.search(r"^\s+if:", block, flags=re.MULTILINE)
    assert "actions/checkout" in block
    assert "softprops/action-gh-release" in block
    assert "python -m build" not in block


def test_release_workflow_publishes_committed_dist_artifacts():
    """@brief TST-021 (DES-042): release assets come from committed dist/.

    @details expected_output = none; expected_exception = AssertionError
            when the release job does not upload the committed `dist/`
            files (with fail-on-unmatched enforcement) or the publish job
            does not check out the tagged commit before publishing.
    """
    release_block = _workflow_job_block("release")
    publish_block = _workflow_job_block("publish-pypi")
    assert "subject-path: dist/*" in release_block
    assert "files: dist/**/*" in release_block
    assert "fail_on_unmatched_files: true" in release_block
    assert "actions/checkout" in publish_block


def test_release_workflow_runs_no_build_or_release_checks():
    """@brief TST-021 (DES-043): no build or build-preparatory step runs.

    @details expected_output = none; expected_exception = AssertionError
            when the workflow references `scripts/build.sh`,
            `scripts/pre-release-check.sh`, any package build command, or
            any build-preparatory toolchain setup step.
    """
    workflow_text = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "scripts/build.sh" not in workflow_text
    assert "pre-release-check.sh" not in workflow_text
    assert "python -m build" not in workflow_text
    assert "Set up Python" not in workflow_text
    assert "Set up uv" not in workflow_text
    assert "setup-python" not in workflow_text
    assert "setup-uv" not in workflow_text


## @brief Packaging metadata file exercised by the PyPI classifier
#         acceptance contract; `project.classifiers` is core metadata
#         validated by the PyPI upload endpoint (DES-016, DES-017).
PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"

## @brief Classifier literal rejected by the PyPI upload endpoint with
#         `400 Bad Request: is not a valid classifier` (defect evidence).
PYPI_REJECTED_CLASSIFIER = (
    "Topic :: Software Development :: Configuration Management"
)

## @brief Golden allowlist of PyPI-valid trove classifiers; every
#         `project.classifiers` entry MUST be a member in this order.
PYPI_VALID_CLASSIFIERS = (
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Utilities",
)


def test_pyproject_classifiers_are_pypi_accepted():
    """@brief Packaging contract: every classifier uploads to PyPI.

    @details expected_output = none; expected_exception = AssertionError
            when the tracked `pyproject.toml` declares the PyPI-rejected
            classifier literal or any classifier outside the PyPI-valid
            golden allowlist. Parses the tracked file read-only (same
            contract-fixture strategy as the workflow tests above);
            complexity: O(C) over declared classifiers C.
    """
    metadata = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    classifiers = tuple(metadata["project"]["classifiers"])
    assert PYPI_REJECTED_CLASSIFIER not in classifiers
    assert classifiers == PYPI_VALID_CLASSIFIERS


## @brief Release-artifact directory exercised by the dist/ packaging
#         contract; `.github/workflows/release-pypi.yml` publishes the
#         tracked `dist/` files verbatim at the tagged commit (DES-042),
#         so their embedded core metadata is a release-blocking contract.
DIST_DIR = Path(__file__).resolve().parents[1] / "dist"


def _dist_artifact_paths():
    """@brief Collect the tracked release artifacts from dist/.

    @details Returns the first-level wheels (`*.whl`) and sdists
            (`*.tar.gz`) sorted by file name so assertions stay
            order-stable; every other dist/ entry is ignored. Read-only
            filesystem access. Complexity: O(A) over artifacts A.
    @return {List[Path]} Sorted artifact paths; empty when dist/ is
            absent.
    """
    if not DIST_DIR.is_dir():
        return []
    candidates = sorted(DIST_DIR.iterdir(), key=lambda item: item.name)
    return [
        item for item in candidates
        if item.is_file() and item.name.endswith((".whl", ".tar.gz"))
    ]


def _artifact_core_metadata(path):
    """@brief Extract the RFC 822 core-metadata block of one artifact.

    @details Wheels expose `<name>-<version>.dist-info/METADATA`;
            sdists expose `<name>-<version>/PKG-INFO`; both header
            blocks are parsed with `email.message_from_string`.
            Read-only archive access. Complexity: O(S) over archive
            bytes S.
    @param path {Path} Release artifact ending in `.whl` or `.tar.gz`.
    @return {email.message.Message} Parsed core metadata exposing the
            `Version` header and the repeated `Classifier` headers.
    @throws {StopIteration} If the archive carries no core-metadata
            member (structurally invalid artifact, DES-033 contract).
    @throws {AssertionError} If the located PKG-INFO member is not an
            extractable regular file (defensive `Optional` narrowing).
    """
    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            member = next(
                name for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            )
            text = archive.read(member).decode("utf-8")
    else:
        with tarfile.open(path, "r:gz") as archive:
            info = next(
                item for item in archive.getmembers()
                if item.isfile() and item.name.endswith("/PKG-INFO")
            )
            member_file = archive.extractfile(info)
            assert member_file is not None, "PKG-INFO must be extractable"
            text = member_file.read().decode("utf-8")
    return email.message_from_string(text)


def test_dist_artifacts_metadata_match_pyproject_and_pypi_acceptance():
    """@brief Packaging contract: dist/ artifacts carry pyproject metadata.

    @details expected_output = none; expected_exception = AssertionError
            when dist/ lacks the sdist-plus-wheel publishing pair, any
            artifact embeds the PyPI-rejected classifier literal, or any
            artifact's embedded `Version`/`Classifier` core metadata
            diverges from the tracked `pyproject.toml` declarations
            (staleness the release workflow would publish verbatim;
            DES-017, DES-042). Parses the tracked artifacts read-only
            (same contract-fixture strategy as the pyproject test
            above); complexity: O(A*S) over artifacts A and bytes S.
    """
    metadata = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    expected_version = metadata["project"]["version"]
    expected_classifiers = tuple(metadata["project"]["classifiers"])
    artifacts = _dist_artifact_paths()
    wheels = [item for item in artifacts if item.name.endswith(".whl")]
    sdists = [item for item in artifacts if item.name.endswith(".tar.gz")]
    assert wheels, "dist/ must hold at least one wheel for publishing"
    assert sdists, "dist/ must hold at least one sdist for publishing"
    for artifact in artifacts:
        artifact_metadata = _artifact_core_metadata(artifact)
        classifiers = tuple(artifact_metadata.get_all("Classifier") or ())
        assert PYPI_REJECTED_CLASSIFIER not in classifiers
        assert artifact_metadata["Version"] == expected_version
        assert classifiers == expected_classifiers


## @brief Repository tooling scripts exercised by TST-022 and TST-023;
#         resolved relative to this test file so the suite stays
#         location-independent.
CLEAN_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "clean.sh"
)
BUILD_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "build.sh"
)
PREFLIGHT_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "pre-release-check.sh"
)

## @brief Execution-generated paths seeded into the sandbox repository
#         (DES-046, DES-047, DES-048): tool caches, build intermediates,
#         the uv virtual environment, nested bytecode caches and package
#         metadata, and coverage data files.
SANDBOX_GENERATED_PATHS = (
    ".pytest_cache/CACHEDIR.TAG",
    ".ruff_cache/0.1.2/synthetic.log",
    ".mypy_cache/3.11/synthetic.json",
    "build/lib/synthetic_pkg.py",
    ".venv/pyvenv.cfg",
    "src/synthetic_pkg/__pycache__/synthetic_module.cpython-311.pyc",
    "src/githubtemplateastraluv.egg-info/PKG-INFO",
    ".coverage",
    ".coverage.host.12345.67890",
)

## @brief Content the cleaner MUST preserve (DES-050): one commit-tracked
#         file, one untracked user file, and one versioned `dist/` release
#         artifact.
SANDBOX_PRESERVED_PATHS = (
    "tracked.txt",
    "notes.txt",
    "dist/githubtemplateastraluv-0.0.0.tar.gz",
)


def _sandbox_git(repo, *args):
    """@brief Run one git command inside the sandbox repository.

    @details Passes throwaway committer identity options so the commit
             works without inheriting any developer git configuration.
    @param repo {Path} Sandbox repository root.
    @param args {tuple[str, ...]} Git argv executed after the repo flag.
    @return {None}
    """
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=dev",
         "-c", "user.email=dev@example.invalid", *args],
        check=True, capture_output=True,
    )


@pytest.fixture
def sandbox_repo(tmp_path):
    """@brief Create a disposable git repository seeded for TST-022.

    @details Lives under `tmp_path` in a directory whose name contains
             spaces (DES-044); carries the copied `scripts/clean.sh`, one
             commit-tracked file, one untracked user file, a `dist/`
             release artifact, and every generated path of
             `SANDBOX_GENERATED_PATHS`. The real repository is never
             touched.
    @param tmp_path {Path} pytest per-test temporary directory.
    @return {Path} The sandbox repository root.
    """
    repo = tmp_path / "sandbox repo with spaces"
    (repo / "scripts").mkdir(parents=True)
    shutil.copyfile(CLEAN_SCRIPT_PATH, repo / "scripts" / "clean.sh")
    (repo / "scripts" / "clean.sh").chmod(0o755)
    (repo / "tracked.txt").write_text("tracked content\n", encoding="utf-8")
    for relative in SANDBOX_GENERATED_PATHS:
        seeded = repo / relative
        seeded.parent.mkdir(parents=True, exist_ok=True)
        seeded.write_text("synthetic generated bytes\n", encoding="utf-8")
    (repo / "dist").mkdir(exist_ok=True)
    (repo / "dist" / "githubtemplateastraluv-0.0.0.tar.gz").write_text(
        "release artifact bytes\n", encoding="utf-8"
    )
    _sandbox_git(repo, "init", "-q")
    _sandbox_git(repo, "add", "tracked.txt")
    _sandbox_git(repo, "commit", "-qm", "sandbox init")
    (repo / "notes.txt").write_text(
        "untracked user content\n", encoding="utf-8"
    )
    return repo


def _run_sandbox_clean(repo):
    """@brief Execute the sandbox copy of `scripts/clean.sh`.

    @param repo {Path} Sandbox repository root used as the child cwd.
    @return {subprocess.CompletedProcess[str]} Completed run record.
    """
    return subprocess.run(
        ["bash", str(repo / "scripts" / "clean.sh")],
        cwd=str(repo), capture_output=True, text=True,
    )


def test_clean_script_removes_generated_paths_and_preserves_content(
    sandbox_repo,
):
    """@brief TST-022 (DES-045..DES-050): the first run cleans, never harms.

    @details expected_output = per-target cleanup log; expected_exception
            = AssertionError when the run exits non-zero, any generated
            path survives, or any tracked, untracked, or `dist/` content
            is deleted.
    @param sandbox_repo {Path} Seeded sandbox repository fixture.
    """
    result = _run_sandbox_clean(sandbox_repo)
    assert result.returncode == 0, result.stderr
    for relative in SANDBOX_GENERATED_PATHS:
        assert not (sandbox_repo / relative).exists(), relative
    for relative in SANDBOX_PRESERVED_PATHS:
        assert (sandbox_repo / relative).is_file(), relative
    assert "==> [CLEAN] removed:" in result.stdout
    assert "dist/ release artifacts preserved." in result.stdout


def test_clean_script_second_run_is_removal_free_noop(sandbox_repo):
    """@brief TST-022 (DES-049): the second run is an idempotent no-op.

    @details expected_output = skip log only; expected_exception =
            AssertionError when the second run exits non-zero, removes
            anything, or does not report the absent targets as skipped.
    @param sandbox_repo {Path} Seeded sandbox repository fixture.
    """
    assert _run_sandbox_clean(sandbox_repo).returncode == 0
    second = _run_sandbox_clean(sandbox_repo)
    assert second.returncode == 0, second.stderr
    assert "==> [CLEAN] removed:" not in second.stdout
    assert "absent, skipping:" in second.stdout


def test_clean_script_static_contract():
    """@brief TST-022 (DES-044, DES-045): the static script contract holds.

    @details expected_output = none; expected_exception = AssertionError
            when the script is missing, not executable, syntactically
            invalid, not git-root-resolved, missing the toolchain gate,
            or carrying a destructive git command or a `dist/` removal
            target (CTN-011, DES-050).
    """
    assert CLEAN_SCRIPT_PATH.is_file()
    assert os.access(CLEAN_SCRIPT_PATH, os.X_OK)
    syntax = subprocess.run(
        ["bash", "-n", str(CLEAN_SCRIPT_PATH)],
        capture_output=True, text=True,
    )
    assert syntax.returncode == 0, syntax.stderr
    text = CLEAN_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "set -Eeuo pipefail" in text
    assert "command -v git" in text
    assert "rev-parse --show-toplevel" in text
    assert "git clean" not in text
    assert "git reset" not in text
    assert "-path ./dist -prune" in text
    assert not re.search(r"remove_target[^\n]*dist", text)


def test_build_script_delegates_prebuild_cleanup_before_any_build_action():
    """@brief TST-023 (DES-051, CTN-011): build.sh delegates, never destroys.

    @details expected_output = none; expected_exception = AssertionError
            when `scripts/build.sh` does not invoke `scripts/clean.sh`
            after the toolchain loop and before the `dist/` stale-artifact
            removal and the build command, or when any of the three
            tooling scripts contains a destructive git command.
    """
    text = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
    toolchain_pos = text.index("for build_tool in git uv")
    clean_pos = text.index('bash "${SCRIPT_DIR}/clean.sh"')
    dist_pos = text.index("DIST_DIR=")
    # rindex anchors the real invocation, not the header-documentation
    # mention of the build command.
    build_pos = text.rindex("python -m build")
    assert toolchain_pos < clean_pos < dist_pos < build_pos
    for script_path in (
        BUILD_SCRIPT_PATH, CLEAN_SCRIPT_PATH, PREFLIGHT_SCRIPT_PATH,
    ):
        script_text = script_path.read_text(encoding="utf-8")
        assert "git clean" not in script_text
        assert "git reset --hard" not in script_text


EXPECTED_PRINT_TREE_STALE_SCHEMA = "\n".join(
    [
        "Application_Configuration - Current configuration",
        "└── version_check - [Path: version_check] Online version check"
        " executed before argument parsing.",
        "    └── disable-version-check = \"no\" (default)",
        "        ╭─────┬───────╮",
        "        │ Sel │ Value │",
        "        ╞═════╪═══════╡",
        "        │ [*] │ \"no\"  │",
        "        ├─────┼───────┤",
        "        │ [ ] │ \"yes\" │",
        "        ╰─────┴───────╯",
    ]
)

EXPECTED_INFO_TREE_STALE_SCHEMA = "\n".join(
    [
        "Application_Configuration - Configuration schema and command"
        " reference",
        "└── version_check - [Path: version_check] Online version check"
        " executed before argument parsing.",
        "    Full overwrite : --set version_check"
        " '{\"disable-version-check\":\"no\"}'",
        "    Reset block : --unset version_check",
        "    └── disable-version-check - [Selection: 2 allowed values]"
        " Disable the automatic online version check executed before"
        " argument parsing; --ver and --version stay active.",
        "        Default : \"no\" (restored via:"
        " --unset version_check:disable-version-check)",
        "        Set cmd : --set version_check:disable-version-check no",
        "        Allowed Values:",
        "        ╭───────┬─────────┬─────────╮",
        "        │ Value │ Default │ Meaning │",
        "        ╞═══════╪═════════╪═════════╡",
        "        │ no    │ default │ -       │",
        "        ├───────┼─────────┼─────────┤",
        "        │ yes   │         │ -       │",
        "        ╰───────┴─────────┴─────────╯",
    ]
)


def test_print_and_info_render_schema_tree_from_stale_schema_file(
    isolated_home, capsys,
):
    """@brief Stale-schema reproducer: schema drift never blocks rendering.

    @details UUTs: config_render.handle_print, config_render.handle_info
            (L1 composed). expected_output = exit status 0 for both
            commands, the schema-shaped `Application_Configuration`
            golden trees on stdout, empty stderr, and a byte-identical
            configuration file; expected_exception = AssertionError.
            A file persisted by an older schema version (the removed
            Notifications section) is not schema-displayable (DES-010)
            and MUST NOT abort the schema-driven renderers: the golden
            schema-shaped output carrying the current `version_check`
            schema section is mandated (TST-008, REQ-019, REQ-042,
            REQ-023).
    @param isolated_home {Path} Fixture redirecting `$HOME` into tmp_path.
    @param capsys {pytest.CaptureFixture} Stdout/stderr capture.
    @return {None}
    """
    configuration_file = (
        isolated_home / ".config" / "githubtemplateastraluv" / "config.json"
    )
    configuration_file.parent.mkdir(parents=True, exist_ok=True)
    stale_payload = (
        '{"Notifications": {"new_version_color": "bright_green", '
        '"error_color": "bright_red"}}\n'
    )
    configuration_file.write_text(stale_payload, encoding="utf-8")

    assert config_render.handle_print(["--print"]) == 0
    assert config_render.handle_info(["--info"]) == 0

    captured = capsys.readouterr()
    assert captured.out == (
        EXPECTED_PRINT_TREE_STALE_SCHEMA
        + "\n"
        + EXPECTED_INFO_TREE_STALE_SCHEMA
        + "\n"
    )
    assert captured.err == ""
    assert configuration_file.read_text(encoding="utf-8") == stale_payload


def test_version_check_parameter_config_cli_round_trip(
    isolated_home, capsys
):
    """@brief TST-010: canonical `version_check` paths round-trip.

    @details UUTs: config.handle_set, config.handle_get,
            config.handle_unset, config_render.handle_print (L1
            composed). expected_output = `--set` exits 0 silently,
            `--get` prints the JSON-quoted value, `--unset` exits 0
            silently restoring the schema default, an unknown path exits
            1 with an `Error: ` stderr diagnostic and empty stdout,
            version_check_disabled() tracks the stored value (REQ-042,
            REQ-043), and `--print` renders the parameter;
            expected_exception = none.
    """
    config.ensure_bootstrapped()
    assert config.handle_set(
        ["--set", "version_check:disable-version-check", "yes"]
    ) == 0
    assert config.handle_get(
        ["--get", "version_check:disable-version-check"]
    ) == 0
    assert capsys.readouterr().out == "\"yes\"\n"
    assert config.version_check_disabled() is True

    assert config.handle_unset(
        ["--unset", "version_check:disable-version-check"]
    ) == 0
    assert config.handle_get(
        ["--get", "version_check:disable-version-check"]
    ) == 0
    assert capsys.readouterr().out == "\"no\"\n"
    assert config.version_check_disabled() is False

    assert config.handle_get(["--get", "nosuchsection"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("Error: ")

    assert config_render.handle_print(["--print"]) == 0
    assert "disable-version-check" in capsys.readouterr().out


## @brief Repository root anchoring the file-level contract fixtures
#         (gitignore, launcher, README, pyproject) exercised next.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

## @brief Launcher script contract target (TST-029).
LAUNCHER_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "templateastraluv.sh"

## @brief Restricted PATH excluding `uv` for the CTN-012 sandbox probe.
RESTRICTED_PATH = "/usr/bin:/bin"


def test_notification_colors_embedded_json_contract(
    isolated_home, capsys
):
    """@brief TST-011 (REQ-026/REQ-041): notifications use embedded JSON.

    @details UUTs: colors.notification_colors (L0),
            version_check.run_version_check (L1 composed).
            expected_output = the embedded JSON assigns bright_green and
            bright_red, the resolved ANSI SGR prefixes equal the 92/91
            literals, and the rendered availability and failure notes
            start with exactly those prefixes and end with the reset
            suffix; expected_exception = none.
    """
    embedded = json.loads(colors.COLOR_CONFIG_JSON)
    assert embedded["notifications"] == {
        "new_version_color": "bright_green",
        "error_color": "bright_red",
    }
    prefixes = colors.notification_colors()
    assert prefixes == {
        "new_version_color": "\033[92m",
        "error_color": "\033[91m",
    }
    with mock.patch.object(
        version_check.urllib.request,
        "urlopen",
        _mock_urlopen({"info": {"version": "9.9.9"}}),
    ):
        version_check.run_version_check("0.0.0")
    out = capsys.readouterr().out
    assert out.startswith(prefixes["new_version_color"])
    assert out.endswith("\033[0m\n")
    _cache_file(isolated_home).unlink()
    http_error = urllib.error.HTTPError(
        EXPECTED_PYPI_ENDPOINT,
        503,
        "Service Unavailable",
        email.message.Message(),
        None,
    )
    with mock.patch.object(
        version_check.urllib.request,
        "urlopen",
        mock.Mock(side_effect=http_error),
    ):
        version_check.run_version_check("0.0.0")
    out = capsys.readouterr().out
    assert out.startswith(prefixes["error_color"])
    assert out.endswith("\033[0m\n")


def test_print_tree_edges_match_schema_and_details_carry_owner_prefix(
    isolated_home,
):
    """@brief TST-009: rendered tree matches schema topology and prefixes.

    @details UUTs: config_render.build_print_root,
            config_render.render_tree (L1). expected_output = the
            edge-marked node count equals sections plus parameters from
            config.SCHEMA, every non-node line carries only
            continuation-prefix segments and never an edge marker, and
            every section heading embeds `[Path: <token>]`;
            expected_exception = none.
    """
    config.ensure_bootstrapped()
    payload = config.load_display()
    root = config_render.build_print_root(payload, None)
    lines = config_render.render_tree(root).split("\n")
    edge = re.compile(r"^(?:│   |    )*(?:├── |└── )")
    node_lines = [line for line in lines if edge.match(line)]
    expected_nodes = len(config.SCHEMA) + sum(
        len(section.params) for section in config.SCHEMA
    )
    assert len(node_lines) == expected_nodes
    assert lines[0] == (
        "Application_Configuration - Current configuration"
    )
    for section in config.SCHEMA:
        assert any(
            f"[Path: {section.token}]" in line for line in node_lines
        )
    for line in lines[1:]:
        if not edge.match(line):
            assert re.match(r"^(?:│   |    )+", line)
            assert not re.search(r"├── |└── ", line)


def test_print_and_info_tables_follow_glyph_contract(
    isolated_home, capsys
):
    """@brief TST-024 (DES-053..DES-056): box-drawing glyph contract.

    @details UUTs: config_render.handle_print,
            config_render.handle_info (L1 composed). expected_output =
            every non-ASCII character belongs to the mandated table
            glyph set plus the tree last-child connector `└`, every
            glyph line matches the rounded-corner border grammar
            (top `╭─┬╮`, bottom `╰─┴╯`, double-line header separator
            `╞═╪╡`, single-line row separator `├─┼┤`, data rows `│...│`),
            and each border kind occurs; expected_exception = none.
    """
    config.ensure_bootstrapped()
    assert config_render.handle_print(["--print"]) == 0
    assert config_render.handle_info(["--info"]) == 0
    out = capsys.readouterr().out
    allowed = set("─│╭╮╰╯├┤┬┴┼═╞╪╡└")
    edge_line = re.compile(r"^(?:│   |    )*(?:├── |└── )")
    shape = re.compile(
        r"^(?:│   |    )*(╭[─┬]*╮|╰[─┴]*╯|╞[═╪]*╡|├[─┼]*┤|│.*)$"
    )
    borders = {"top": 0, "bottom": 0, "header": 0, "row": 0}
    for line in out.split("\n"):
        glyphs = {c for c in line if ord(c) > 127}
        assert glyphs <= allowed
        if not glyphs or edge_line.match(line):
            continue
        assert shape.match(line)
        stripped = re.sub(r"^(?:│   |    )*", "", line)
        if stripped.startswith("╭"):
            borders["top"] += 1
        elif stripped.startswith("╰"):
            borders["bottom"] += 1
        elif stripped.startswith("╞"):
            borders["header"] += 1
        elif stripped.startswith("├"):
            borders["row"] += 1
    assert all(count > 0 for count in borders.values())


def test_gitignore_keeps_dist_traversable():
    """@brief TST-019 (DES-040): dist/ stays selectively re-includable.

    @details expected_output = `git check-ignore -v --no-index`
            resolves every probed `dist/` path to the `!dist/` or
            `!dist/**/*` re-include rule (last matching pattern),
            proving selective re-inclusion of versionable files;
            expected_exception = none.
    """
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!dist/" in gitignore
    assert "!dist/**/*" in gitignore
    for probe in ("dist/probe.whl", "dist/nested/probe.tar.gz"):
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "check-ignore",
             "-v", "--no-index", probe],
            capture_output=True,
            text=True,
        )
        fields = result.stdout.rstrip("\n").split("\t")
        assert len(fields) == 2, (probe, result.stdout, result.stderr)
        assert "!dist/" in fields[0], (probe, result.stdout)


def test_release_workflow_runs_on_pinned_ubuntu_2404():
    """@brief TST-020 (DES-041): every job pins ubuntu-24.04.

    @details expected_output = every `runs-on:` value equals
            `ubuntu-24.04` and no `ubuntu-latest` label occurs anywhere
            in the release workflow; expected_exception = none.
    """
    text = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")
    runs_on = re.findall(r"^\s*runs-on:\s*(\S+)\s*$", text, re.MULTILINE)
    assert runs_on
    assert set(runs_on) == {"ubuntu-24.04"}
    assert "ubuntu-latest" not in text


def test_pyproject_build_system_requires_setuptools_77_without_wheel():
    """@brief TST-030 (DES-057): build-system floor matches PEP 639.

    @details expected_output = build-system requires contains exactly
            the `setuptools>=77.0.0` floor and `build>=1.0.0`, with no
            `wheel` entry; expected_exception = none.
    """
    metadata = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    requires = metadata["build-system"]["requires"]
    assert requires == ["setuptools>=77.0.0", "build>=1.0.0"]


def test_pyproject_declares_dual_entry_points():
    """@brief TST-031 (DES-003, REQ-048): exactly two console-script
            entry points.

    @details expected_output = `project.scripts` maps exactly
            `githubtemplateastraluv` (long name) and `templateastraluv`
            (short name) to the same `githubtemplateastraluv.__main__:main`
            CLI function; no other entry point exists;
            expected_exception = none.
    """
    metadata = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    assert metadata["project"]["scripts"] == {
        "githubtemplateastraluv": "githubtemplateastraluv.__main__:main",
        "templateastraluv": "githubtemplateastraluv.__main__:main",
    }


def test_readme_command_and_configuration_documentation_contract():
    """@brief TST-032 (DES-059/DES-060): README stays behavior-consistent.

    @details expected_output = README carries the exact REQ-003 upgrade
            argv and the REQ-032 develop argv, documents the
            `version_check:disable-version-check` parameter, and keeps
            no stale schema-empty or configurable-color claims;
            expected_exception = none.
    """
    text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "`uv tool upgrade githubtemplateastraluv`" in text
    assert (
        "`uv tool install githubtemplateastraluv --reinstall --from "
        "git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git@develop`"
        in text
    )
    assert "version_check:disable-version-check" in text
    assert "currently defines no sections" not in text
    assert "notification-color subsystem" not in text


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="permission bits do not block the root user",
)
def test_cache_write_failure_does_not_abort_dispatch(
    isolated_home, capsys
):
    """@brief TST-027 (REQ-046): unwritable cache never aborts the CLI.

    @details UUT: core.main (L2). expected_output = with a read-only
            `$HOME/.cache` directory and a mocked newer PyPI release,
            the green note prints, the gated check returns normally,
            the help screen dispatches, and the exit code is 0 with no
            traceback; expected_exception = none.
    """
    cache_dir = isolated_home / ".cache"
    cache_dir.mkdir()
    cache_dir.chmod(0o500)
    try:
        with mock.patch.object(
            version_check.urllib.request,
            "urlopen",
            _mock_urlopen({"info": {"version": "9.9.9"}}),
        ):
            exit_code = core.main([])
    finally:
        cache_dir.chmod(0o700)
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "New version available: 9.9.9" in out
    assert out.endswith(EXPECTED_HELP_TEXT + "\n")


def test_parse_version_tolerates_non_integer_components(
    isolated_home, capsys
):
    """@brief TST-028 (REQ-047): tolerant leading-integer version parse.

    @details UUTs: version_check._parse_version (L0),
            version_check.run_version_check (L1 composed).
            expected_output = suffix components map to their leading
            integers, and a mocked `9.9.9rc1` release prints the green
            availability note comparing against `0.0.1` with a 3600 s
            cache refresh instead of the red failure note;
            expected_exception = none.
    """
    assert version_check._parse_version("0.0.7rc1") == (0, 0, 7)
    assert version_check._parse_version("v2") == (2,)
    assert version_check._parse_version("v1.2.x") == (1, 2, 0)
    assert version_check._parse_version("") == (0,)
    with mock.patch.object(
        version_check.urllib.request,
        "urlopen",
        _mock_urlopen({"info": {"version": "9.9.9rc1"}}),
    ):
        version_check.run_version_check("0.0.1")
    out = capsys.readouterr().out
    assert "New version available: 9.9.9rc1" in out
    assert "(installed version: 0.0.1)" in out
    assert "\033[91m" not in out
    _assert_cache_fields(isolated_home, 3600)


def _copy_project_skeleton(target):
    """@brief Copy the build-relevant project tree into a sandbox.

    @details Copies `scripts/`, `src/`, packaging metadata, lock,
             README, LICENSE, and `.gitignore` into `target`, then
             initializes a git repository and stages every copied path
             so `git ls-files`-driven checks enumerate them.
    @param target {Path} Sandbox repository root (existing directory).
    @return {None}
    """
    for directory in ("scripts", "src"):
        shutil.copytree(PROJECT_ROOT / directory, target / directory)
    for name in (
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "LICENSE",
        ".gitignore",
    ):
        shutil.copyfile(PROJECT_ROOT / name, target / name)
    _sandbox_git(target, "init", "-q")
    _sandbox_git(target, "add", "-A")


def _sandbox_environment():
    """@brief Build the child environment for sandboxed tooling runs.

    @details Copies the current environment minus `VIRTUAL_ENV`, so
             sandboxed `uv run` invocations always manage their own
             sandbox virtual environment.
    @return {dict[str, str]} Environment mapping for subprocess.run.
    """
    environment = dict(os.environ)
    environment.pop("VIRTUAL_ENV", None)
    return environment


def test_build_script_double_run_is_clean_and_idempotent(tmp_path):
    """@brief TST-016 (DES-021..DES-025, DES-052): two builds, one pair.

    @details expected_output = both sandboxed `scripts/build.sh` runs
            exit 0 with the `[CLEAN]` pre-build delegation logged, the
            seeded stale distribution artifact disappears, and `dist/`
            ends holding exactly one sdist and one wheel for the
            version declared in the sandbox `pyproject.toml`
            (`project.version` parsed with `tomllib`; artifact names
            are derived, never hardcoded, so version bumps cannot
            desynchronize the expectation); expected_exception = none.
            Isolation: disposable git sandbox under tmp_path; uv
            provisions build tooling from the local uv cache.
    @param tmp_path {Path} pytest per-test temporary directory.
    """
    repo = tmp_path / "build sandbox"
    repo.mkdir()
    _copy_project_skeleton(repo)
    stale = repo / "dist" / "githubtemplateastraluv-0.0.0.tar.gz"
    stale.parent.mkdir()
    stale.write_text("stale bytes\n", encoding="utf-8")
    environment = _sandbox_environment()
    first = subprocess.run(
        ["bash", str(repo / "scripts" / "build.sh")],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert first.returncode == 0, first.stderr
    second = subprocess.run(
        ["bash", str(repo / "scripts" / "build.sh")],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert second.returncode == 0, second.stderr
    for run in (first, second):
        assert "==> [CLEAN] project root:" in run.stdout
    assert not stale.exists()
    artifacts = sorted(
        item.name for item in (repo / "dist").iterdir() if item.is_file()
    )
    declared_version = tomllib.loads(
        (repo / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    assert artifacts == [
        f"githubtemplateastraluv-{declared_version}-py3-none-any.whl",
        f"githubtemplateastraluv-{declared_version}.tar.gz",
    ]


def _copy_project_with_dummy_tests(target):
    """@brief Copy the project skeleton plus a minimal dummy test suite.

    @details Replacement `tests/` payload for pre-release-check
             sandboxes: the inner `uv run pytest` phase executes only
             the dummy module, preventing suite recursion.
    @param target {Path} Sandbox repository root (existing directory).
    @return {None}
    """
    _copy_project_skeleton(target)
    (target / "tests").mkdir()
    (target / "tests" / "test_sandbox_dummy.py").write_text(
        "def test_sandbox_dummy():\n    assert True\n", encoding="utf-8"
    )
    _sandbox_git(target, "add", "-A")


def test_pre_release_check_passes_and_leaves_clean_tree(tmp_path):
    """@brief TST-017 (DES-026..DES-038): full verification run.

    @details expected_output = the sandboxed
            `scripts/pre-release-check.sh` exits 0 reporting the success
            summary, and the sandbox `git status --porcelain --ignored`
            equals the pre-execution baseline after the trap-based
            cleanup; expected_exception = none.
    @param tmp_path {Path} pytest per-test temporary directory.
    """
    repo = tmp_path / "preflight sandbox"
    repo.mkdir()
    _copy_project_with_dummy_tests(repo)
    baseline = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--ignored"],
        capture_output=True,
        text=True,
    ).stdout
    result = subprocess.run(
        ["bash", str(repo / "scripts" / "pre-release-check.sh")],
        capture_output=True,
        text=True,
        env=_sandbox_environment(),
    )
    assert result.returncode == 0, result.stderr
    assert "all pre-release checks passed" in result.stdout
    final = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--ignored"],
        capture_output=True,
        text=True,
    ).stdout
    assert final == baseline


def test_pre_release_check_failing_tool_reports_phase_and_cleans(tmp_path):
    """@brief TST-018 (DES-027/DES-034/DES-035): failing tool aborts clean.

    @details expected_output = with a failing `uv` shim first on a
            minimal PATH (no `BASH_ENV`, so the shim cannot be shadowed
            by shell startup files), the sandboxed
            `scripts/pre-release-check.sh` exits 1, the stderr
            diagnostic names the first failed phase
            (`python-bytecode-compilation`), the failure summary
            prints, and the sandbox `git status --porcelain --ignored`
            equals the pre-execution baseline;
            expected_exception = none.
    @param tmp_path {Path} pytest per-test temporary directory.
    """
    repo = tmp_path / "failing tool sandbox"
    repo.mkdir()
    _copy_project_with_dummy_tests(repo)
    baseline = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--ignored"],
        capture_output=True,
        text=True,
    ).stdout
    shim_dir = tmp_path / "shim bin"
    shim_dir.mkdir()
    shim = shim_dir / "uv"
    shim.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    shim.chmod(0o755)
    environment = {
        "PATH": str(shim_dir) + os.pathsep + RESTRICTED_PATH,
        "HOME": os.environ.get("HOME", str(repo)),
    }
    result = subprocess.run(
        ["bash", str(repo / "scripts" / "pre-release-check.sh")],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 1
    assert (
        "pre-release check failed: python-bytecode-compilation"
        in result.stderr
    )
    assert "pre-release verification FAILED" in result.stderr
    final = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--ignored"],
        capture_output=True,
        text=True,
    ).stdout
    assert final == baseline


@pytest.mark.skipif(
    shutil.which("git", path=RESTRICTED_PATH) is None,
    reason="git unavailable on the restricted PATH",
)
@pytest.mark.skipif(
    shutil.which("uv", path=RESTRICTED_PATH) is not None,
    reason="uv reachable on the restricted PATH",
)
def test_launcher_missing_uv_exits_nonzero(sandbox_repo):
    """@brief TST-029 (CTN-012): launcher validates uv before delegation.

    @details expected_output = executing the sandboxed launcher on a
            PATH without `uv` exits 1 with the stderr diagnostic
            `ERROR: Required tool not found: uv` and delegates to no
            runtime; expected_exception = none.
    """
    launcher = sandbox_repo / "scripts" / "templateastraluv.sh"
    shutil.copyfile(LAUNCHER_SCRIPT_PATH, launcher)
    launcher.chmod(0o755)
    result = subprocess.run(
        [str(launcher), "--help"],
        capture_output=True,
        text=True,
        env={"PATH": RESTRICTED_PATH, "HOME": str(sandbox_repo)},
    )
    assert result.returncode == 1
    assert "ERROR: Required tool not found: uv" in result.stderr


def test_launcher_static_contract_uses_frozen_delegation():
    """@brief TST-029 (CTN-013): delegation runs frozen against the lock.

    @details expected_output = the launcher guards the delegation with
            `command -v uv` and delegates through
            `uv run --frozen --project` so the tracked `uv.lock` is
            never rewritten; expected_exception = none.
    """
    text = LAUNCHER_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "command -v uv" in text
    assert "run --frozen --project" in text

#!/usr/bin/env python3
## @file test_githubtemplateastraluv.py
# @brief HDT unit suite (Generator mode) covering TST-001..TST-007,
#        TST-012..TST-015, TST-021, TST-022, TST-023 for the
#        githubtemplateastraluv CLI, its release workflow, its
#        repository tooling scripts, and its packaging-artifact contract.
# @details HDT static-analysis artifact (section 7.1):
#          - UUTs and levels: L0 = management.is_linux,
#            management._management_entry, version_check._parse_version,
#            version_check._human_timestamp,
#            version_check._format_report_row; L1 =
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
        "git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git",
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

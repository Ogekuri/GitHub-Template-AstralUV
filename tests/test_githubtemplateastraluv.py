#!/usr/bin/env python3
## @file test_githubtemplateastraluv.py
# @brief HDT unit suite (Generator mode) covering TST-001..TST-007 for the
#        githubtemplateastraluv CLI.
# @details HDT static-analysis artifact (section 7.1):
#          - UUTs and levels: L0 = management.is_linux,
#            management._management_entry, version_check._parse_version,
#            version_check._human_timestamp; L1 = management.build_help_text,
#            management.print_help, management.cmd_upgrade,
#            management.cmd_uninstall, version_check._read_cache,
#            version_check._write_cache, version_check._gate_allows_request,
#            version_check.run_version_check; L2 = core.main.
#          - External dependencies isolated: network (urlopen mocked),
#            filesystem ($HOME redirected into tmp_path), process spawn
#            (subprocess.run mocked), wall clock (tolerance-bounded
#            assertions on the 3600/86400 second deltas).
#          - Execution plan (dev signal): `uv run pytest` from the project
#            root; CI gates L0 -> L1 -> L2 fail-fast outside test bodies.
import email.message
import json
import re
import time
import urllib.error
from unittest import mock

import pytest

import githubtemplateastraluv.core as core
import githubtemplateastraluv.management as management
import githubtemplateastraluv.version_check as version_check

## @brief GitHub endpoint oracle duplicated from the SRS (REQ-009) to keep
#         assertions independent from implementation constants.
EXPECTED_ENDPOINT = (
    "https://api.github.com/repos/Ogekuri/"
    "GitHub-Template-AstralUV/releases/latest"
)

## @brief Independent byte-exact help-screen oracle for TST-001 (REQ-001
#         template with version 0.0.0 substituted into the `(x.y.z)` slot).
EXPECTED_HELP_TEXT = (
    "Usage: githubtemplateastraluv [command] [options] (0.0.0)\n"
    "\n"
    "Management Commands:\n"
    "  --upgrade   - Reinstall githubtemplateastraluv on Linux; print manual"
    " command elsewhere.\n"
    "  --uninstall - Uninstall githubtemplateastraluv on Linux; print manual"
    " command elsewhere.\n"
    "  --ver       - Print the githubtemplateastraluv version.\n"
    "  --version   - Print the githubtemplateastraluv version.\n"
    "  --help      - Print the full help screen or the help text of a"
    " specific command.\n"
    "\n"
    "Commands:\n"
    "  ..."
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


def _mock_urlopen(tag_name):
    """@brief Build a patched `urlopen` returning a release payload.

    @param tag_name {str} Release tag returned by the fake endpoint.
    @return {mock.MagicMock} Context-manager stand-in for urlopen.
    """
    urlopen = mock.MagicMock()
    response = urlopen.return_value.__enter__.return_value
    response.read.return_value = json.dumps(
        {"tag_name": tag_name}
    ).encode("utf-8")
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


def test_ver_prints_version_and_forces_check_despite_fresh_cache(
    isolated_home, capsys, monkeypatch
):
    """@brief TST-002: forced check bypasses an unexpired cache gate.

    @details expected_output = version line matching x.y.z; forced check
            recorded exactly once with force=True.
    """
    _write_cache(isolated_home, time.time() + 9999)
    forced_calls = []
    monkeypatch.setattr(
        version_check,
        "run_version_check",
        lambda installed, force: forced_calls.append(force),
    )
    exit_code = core.main(["--ver"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\n", out)
    assert forced_calls == [True]


def test_upgrade_on_linux_executes_exact_uv_install(isolated_home):
    """@brief TST-003: `--upgrade` spawns the exact REQ-003 argv on Linux.

    @details expected_output = exit code 0 and one subprocess.run call with
            UPGRADE_COMMAND; expected_exception = none.
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
    run_mock.assert_called_once_with(management.UPGRADE_COMMAND, check=False)


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
    """@brief TST-005: cache-miss -> one request, timeout 2, exact endpoint.

    @details expected_output = bright-green note for the newer 9.9.9 tag;
            request URL equals EXPECTED_ENDPOINT and timeout equals 2.
    """
    urlopen_mock = _mock_urlopen("9.9.9")
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        version_check.run_version_check("0.0.0")
    urlopen_mock.assert_called_once()
    request = urlopen_mock.call_args[0][0]
    assert request.get_full_url() == EXPECTED_ENDPOINT
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
    urlopen_mock = _mock_urlopen("0.0.1")
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
    urlopen_mock = _mock_urlopen("v9.9.9")
    with mock.patch.object(
        version_check.urllib.request, "urlopen", urlopen_mock
    ):
        version_check.run_version_check("0.0.0")
    out = capsys.readouterr().out
    assert "\033[92m" in out
    assert "New version available: v9.9.9" in out
    assert "(installed version: 0.0.0)" in out
    _assert_cache_fields(isolated_home, 3600)


def test_equal_release_no_notification_but_cache_refreshed(
    isolated_home, capsys
):
    """@brief TST-006 boundary (A-04): up-to-date -> silent, cache + 3600.

    @details expected_output = empty stdout; cache refreshed with the
            standard idle-delay; expected_exception = none.
    """
    urlopen_mock = _mock_urlopen("0.0.0")
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
        EXPECTED_ENDPOINT, 503, "Service Unavailable", headers, None
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

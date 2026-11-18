#!/usr/bin/env python3
## @file test_githubtemplateastraluv.py
# @brief HDT unit suite (Generator mode) covering TST-001..TST-007,
#        TST-012..TST-015 for the githubtemplateastraluv CLI and its
#        release workflow.
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
#          - Contract checks (TST-012..TST-015): action pins and job
#            topology of `.github/workflows/release-pypi.yml` versus the
#            Node24-or-later manifest (DES-015, CTN-010) plus the PyPI
#            trusted-publisher contract (DES-016, DES-017, DES-018); the
#            tracked workflow file is the read-only deterministic fixture.
#          - Execution plan (dev signal): `uv run pytest` from the project
#            root; CI gates L0 -> L1 -> L2 fail-fast outside test bodies.
import email.message
import json
from pathlib import Path
import re
import time
import urllib.error
from unittest import mock

import pytest

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
        "Current Installed : 0.0.0\n"
        "Latest @ PyPI     : 9.9.9\n"
        "Latest @ GitHub   : 8.8.8\n"
    )
    assert urlopen_mock.call_count == 2
    _assert_cache_fields(isolated_home, 3600)


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


def test_upgrade_develop_on_linux_executes_exact_uv_install(isolated_home):
    """@brief TST-014 (REQ-032): `--upgrade --develop` spawns exact argv.

    @details expected_output = exit code 0 and one subprocess.run call with
            UPGRADE_DEVELOP_COMMAND; expected_exception = none.
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
    run_mock.assert_called_once_with(
        management.UPGRADE_DEVELOP_COMMAND, check=False
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


def test_ver_report_marks_failed_pypi_source_unavailable(
    isolated_home, capsys
):
    """@brief TST-013 (REQ-030/REQ-031): failed PyPI -> unavailable row.

    @details expected_output = `unavailable` in the PyPI row, populated
            GitHub row, bright red note naming PyPI; cache backs off
            86400 s (PyPI outcome only); expected_exception = none
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
    assert "Latest @ PyPI     : unavailable\n" in out
    assert "Latest @ GitHub   : 8.8.8\n" in out
    assert "\033[91m" in out
    assert "@ PyPI" in out
    _assert_cache_fields(isolated_home, 86400)


def test_ver_report_marks_failed_github_source_unavailable(
    isolated_home, capsys
):
    """@brief TST-013 (REQ-030/REQ-031): failed GitHub -> unavailable row.

    @details expected_output = populated PyPI row, `unavailable` in the
            GitHub row, bright red note naming GitHub; cache refreshed
            3600 s (PyPI outcome only); expected_exception = none
            (handled internally).
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
    assert "Latest @ GitHub   : unavailable\n" in out
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
# @details `astral-sh/setup-uv` is a composite action and
#          `pypa/gh-action-pypi-publish` is a Docker action; neither
#          declares a JavaScript runtime, and their entries keep the
#          manifest exhaustive over every `uses:` pin of the release
#          workflow.
NODE24_ACTION_MIN_MAJOR = {
    "actions/checkout": 5,
    "actions/setup-python": 7,
    "astral-sh/setup-uv": 3,
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
            when the declaration-order pin list differs from the migrated
            Node24 stack (two checkout pins, setup-python, setup-uv,
            attest-build-provenance, changelog builder, gh-release, PyPI
            publisher).
    """
    assert _release_workflow_pins() == [
        "actions/checkout@v5",
        "actions/checkout@v5",
        "actions/setup-python@v7",
        "astral-sh/setup-uv@v3",
        "actions/attest-build-provenance@v4",
        "mikepenz/release-changelog-builder-action@v6",
        "softprops/action-gh-release@v3",
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
            permission, or the PyPI trusted-publishing action pin.
    """
    block = _workflow_job_block("publish-pypi")
    assert "needs: [check-branch, build-release]" in block
    assert "needs.check-branch.outputs.is_master == 'true'" in block
    assert "id-token: write" in block
    assert "pypa/gh-action-pypi-publish@release/v1" in block


def test_release_workflow_build_release_runs_for_every_tag():
    """@brief TST-015 (DES-018): build/release run for every canonical tag.

    @details expected_output = none; expected_exception = AssertionError
            when the build-release job carries a branch gate or misses the
            GitHub release step.
    """
    block = _workflow_job_block("build-release")
    assert "is_master" not in block
    assert not re.search(r"^\s+if:", block, flags=re.MULTILINE)
    assert "softprops/action-gh-release" in block

#!/usr/bin/env python3
## @file version_check.py
# @brief Online new-version check and dual-source version report executed
#        before CLI argument parsing.
# @details Queries the PyPI JSON API with a hardcoded 2 s timeout for the
#          gated availability check, throttled through an idle-time JSON
#          cache under `$HOME`, and renders the aligned three-row report
#          (`--ver`) fetching both PyPI and the GitHub releases API.
#          Notifications use the colors configured in the configuration
#          subsystem (REQ-026), falling back to bright green / bright red
#          schema defaults when configuration cannot be loaded. Success
#          refreshes the cache with a 3600 s idle-delay; any failure backs
#          off 86400 s.
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from githubtemplateastraluv import config

## @brief PyPI JSON API endpoint returning latest published version
#        metadata (REQ-009, REQ-028).
_PYPI_JSON_ENDPOINT = "https://pypi.org/pypi/githubtemplateastraluv/json"
## @brief GitHub API endpoint returning latest release metadata; source of
#        the report `Latest @ GitHub` row (REQ-029) and of the
#        `--upgrade --develop` download (REQ-032).
_GITHUB_RELEASES_ENDPOINT = (
    "https://api.github.com/repos/Ogekuri/"
    "GitHub-Template-AstralUV/releases/latest"
)
## @brief HTTP(S) request timeout in seconds, hardcoded (CTN-006).
_HTTP_TIMEOUT_SECONDS = 2
## @brief Idle-delay in seconds after every successful check (CTN-007).
_IDLE_DELAY_SUCCESS_SECONDS = 3600
## @brief Idle-delay in seconds after any failed check (CTN-007).
_IDLE_DELAY_FAILURE_SECONDS = 86400
## @brief Cache file location relative to `$HOME` (DES-007).
_CACHE_RELATIVE_PATH = (
    ".cache",
    "githubtemplateastraluv",
    "check_version_idle-time.json",
)
## @brief ANSI SGR reset suffix closing colored notifications.
# @details Notification prefix colors are configured through the
#          configuration subsystem (config.notification_colors, REQ-026);
#          only the reset suffix stays local.
_ANSI_RESET = "\033[0m"
## @brief Report row label for the installed version (REQ-027).
_REPORT_LABEL_INSTALLED = "Current Installed"
## @brief Report row label for the PyPI latest version (REQ-027).
_REPORT_LABEL_PYPI = "Latest @ PyPI"
## @brief Report row label for the GitHub latest release version (REQ-027).
_REPORT_LABEL_GITHUB = "Latest @ GitHub"
## @brief Label pad width keeping report version columns aligned (REQ-027).
# @details Equals the length of the longest label `_REPORT_LABEL_INSTALLED`.
_REPORT_LABEL_WIDTH = len(_REPORT_LABEL_INSTALLED)
## @brief Placeholder replacing the version of a failed report source
#        before the reason suffix is appended (REQ-030).
_REPORT_UNKNOWN = "unknown"


def _cache_path() -> Path:
    """@brief Resolve the absolute cache file path from `$HOME`.

    @details Prefers the `HOME` environment variable (CTN-008); falls back
             to `Path.home()` when unset. Does not create directories.
    @return {Path} Absolute cache file path.
    @satisfies DES-007 CTN-008
    """
    if "HOME" in os.environ:
        base = Path(os.environ["HOME"])
    else:
        base = Path.home()
    return base.joinpath(*_CACHE_RELATIVE_PATH)


def _read_cache(path: Path) -> dict[str, Any] | None:
    """@brief Load the idle-time cache JSON document.

    @details Returns None when the file is absent, unreadable, unparsable,
             or not a JSON object; callers treat None as cache-miss.
    @param path {Path} Cache file path.
    @return {dict[str, Any] | None} Parsed cache payload or None.
    @satisfies REQ-008
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _human_timestamp(epoch_seconds: float) -> str:
    """@brief Format an epoch value as UTC ISO-8601.

    @param epoch_seconds {float} Epoch seconds to render.
    @return {str} Timestamp shaped `YYYY-MM-DDTHH:MM:SSZ`.
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch_seconds))


def _write_cache(
    path: Path,
    check_epoch: float,
    idle_delay_seconds: int,
) -> None:
    """@brief Persist the four-field idle-time cache document.

    @details Creates missing parent directories. Field names follow A-03.
    @param path {Path} Cache file path.
    @param check_epoch {float} Epoch seconds of the check attempt.
    @param idle_delay_seconds {int} Idle-delay applied after this check.
    @return {None}
    @post Cache file holds exactly four fields: last_check_epoch,
          last_check_human, idle_time_epoch, idle_time_human.
    @satisfies REQ-010 REQ-011 DES-007
    """
    idle_epoch = int(check_epoch) + idle_delay_seconds
    payload = {
        "last_check_epoch": int(check_epoch),
        "last_check_human": _human_timestamp(check_epoch),
        "idle_time_epoch": idle_epoch,
        "idle_time_human": _human_timestamp(idle_epoch),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _gate_allows_request(
    cache: dict[str, Any] | None,
    now_epoch: float,
) -> bool:
    """@brief Evaluate the idle-time request gate.

    @details Gate opens on cache-miss (None), non-numeric idle_time_epoch,
             or `now_epoch >= idle_time_epoch`; otherwise it stays closed.
    @param cache {dict[str, Any] | None} Parsed cache payload or None.
    @param now_epoch {float} Current epoch seconds.
    @return {bool} True when an HTTPS request is permitted.
    @satisfies REQ-008
    """
    if cache is None:
        return True
    idle_epoch = cache.get("idle_time_epoch")
    if not isinstance(idle_epoch, (int, float)):
        return True
    return now_epoch >= idle_epoch


def _parse_version(version: str) -> tuple[int, ...]:
    """@brief Parse a dotted version string into a comparable tuple.

    @details Strips one leading `v`/`V` prefix before splitting on dots.
    @param version {str} Version or release tag (e.g. `v1.2.3`).
    @return {tuple[int, ...]} Comparable component tuple.
    @throws {ValueError} If any component is not an integer.
    """
    text = version[1:] if version[:1] in ("v", "V") else version
    return tuple(int(part) for part in text.split("."))


def _fetch_latest_pypi_version() -> str:
    """@brief GET the PyPI JSON payload and extract the latest version.

    @details Sends a plain GET to the PyPI JSON API; no Accept header is
             required. Payload shape: `{"info": {"version": "x.y.z"}}`.
    @return {str} Latest published version in `x.y.z` format.
    @throws {urllib.error.URLError} On HTTP and network failures; includes
            HTTPError carrying the status code (e.g. 429, 503).
    @throws {TimeoutError} On the 2-second timeout expiry.
    @throws {ValueError} On unparsable payload or missing version.
    @satisfies REQ-009 REQ-028 CTN-006
    """
    request = urllib.request.Request(_PYPI_JSON_ENDPOINT)
    with urllib.request.urlopen(
        request, timeout=_HTTP_TIMEOUT_SECONDS
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    info = payload.get("info") if isinstance(payload, dict) else None
    version = info.get("version") if isinstance(info, dict) else None
    if not isinstance(version, str) or not version:
        raise ValueError("PyPI payload misses info.version")
    return version


def _fetch_latest_github_version() -> str:
    """@brief GET the latest GitHub release payload and extract its version.

    @details Strips one leading `v`/`V` prefix from `tag_name`; the returned
             value is exactly the version downloaded by
             `--upgrade --develop` (REQ-032) regardless of the branch the
             release was tagged on.
    @return {str} Latest release version in `x.y.z` format.
    @throws {urllib.error.URLError} On HTTP and network failures; includes
            HTTPError carrying the status code (e.g. 429, 503).
    @throws {TimeoutError} On the 2-second timeout expiry.
    @throws {ValueError} On unparsable payload or missing tag_name.
    @satisfies REQ-029 CTN-006
    """
    request = urllib.request.Request(
        _GITHUB_RELEASES_ENDPOINT,
        headers={"Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(
        request, timeout=_HTTP_TIMEOUT_SECONDS
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag_name = payload.get("tag_name") if isinstance(payload, dict) else None
    if not isinstance(tag_name, str) or not tag_name:
        raise ValueError("release payload misses tag_name")
    return tag_name[1:] if tag_name[:1] in ("v", "V") else tag_name


def _format_report_row(label: str, value: str) -> str:
    """@brief Render one report row with the label padded to 17 columns.

    @param label {str} Row label (e.g. `Latest @ PyPI`).
    @param value {str} Version string or `unknown (<reason>)` placeholder.
    @return {str} Row shaped `<label padded to 17> : <value>` (REQ-027).
    @satisfies REQ-027
    """
    return f"{label:<{_REPORT_LABEL_WIDTH}} : {value}"


def _unknown_value(reason: str) -> str:
    """@brief Render the failed-source placeholder with its reason.

    @details REQ-030 mandates the `unknown (<reason>)` shape, where
             `<reason>` names the actually encountered error (e.g. an
             HTTP 403/404 rate-limit response or a timeout); an empty
             reason degrades to the bare `unknown` placeholder.
    @param reason {str} String rendering of the encountered error.
    @return {str} `unknown (<reason>)`, or `unknown` when reason is empty.
    @satisfies REQ-030
    """
    if not reason:
        return _REPORT_UNKNOWN
    return f"{_REPORT_UNKNOWN} ({reason})"


def _print_colored(color: str, message: str) -> None:
    """@brief Print a message wrapped in an ANSI color prefix and reset.

    @param color {str} ANSI SGR prefix (bright green or bright red).
    @param message {str} Plain-text message content.
    @return {None}
    @satisfies DES-008
    """
    print(f"{color}{message}{_ANSI_RESET}")


def _report_failure(
    check_epoch: float,
    error: BaseException,
    color: str,
) -> None:
    """@brief Emit the failure note and write the 86400 s cache.

    @details The note renders with the configured error color (REQ-026).
    @param check_epoch {float} Epoch seconds of the failed attempt.
    @param error {BaseException} Encountered error rendered in the note.
    @param color {str} ANSI SGR prefix for the failure note.
    @return {None}
    @satisfies REQ-014 REQ-015 REQ-026 A-05
    """
    _print_colored(color, f"Version check failed: {error}")
    _write_cache(_cache_path(), check_epoch, _IDLE_DELAY_FAILURE_SECONDS)


def run_version_check(installed_version: str, force: bool = False) -> None:
    """@brief Execute the gated (or forced) online version check on PyPI.

    @details Flow: cache read -> gate evaluation (skipped when `force`) ->
             PyPI JSON fetch -> version compare -> notify -> cache write.
             Notification colors come from the configuration subsystem
             with schema-default fallback (REQ-026). Success always
             refreshes the cache with the 3600 s idle-delay (REQ-013,
             A-04); fetch or parse failures print the configured error
             note and back off 86400 s (REQ-014, REQ-015, A-05). The call
             always returns normally; callers continue parsing (A-06).
    @param installed_version {str} Installed version in `x.y.z` format.
    @param force {bool} True bypasses the idle-time gate (REQ-002,
           REQ-007).
    @return {None}
    @satisfies REQ-007 REQ-008 REQ-009 REQ-010 REQ-011 REQ-012 REQ-013
               REQ-014 REQ-015 REQ-024 REQ-025 REQ-026
    """
    check_epoch = time.time()
    colors = config.notification_colors()
    cache = _read_cache(_cache_path())
    if not force and not _gate_allows_request(cache, check_epoch):
        return
    try:
        latest_version = _fetch_latest_pypi_version()
        available = _parse_version(latest_version)
        installed = _parse_version(installed_version)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as error:
        _report_failure(check_epoch, error, colors["error_color"])
        return
    if available > installed:
        _print_colored(
            colors["new_version_color"],
            f"New version available: {latest_version} "
            f"(installed version: {installed_version})",
        )
    _write_cache(_cache_path(), check_epoch, _IDLE_DELAY_SUCCESS_SECONDS)


def run_version_report(installed_version: str) -> None:
    """@brief Execute the forced dual-source version report (`--ver`).

    @details Flow: fetch PyPI -> fetch GitHub -> emit the three aligned
             rows. Each failed fetch emits one bright red note naming the
             failed source with the configured error color (REQ-030) and
             its row prints `unknown (<reason>)`, carrying the actually
             encountered error, in place of the version (REQ-030). Rows
             print in order: installed, PyPI, GitHub; version columns
             aligned via a 17-character label pad (REQ-027). The GitHub
             row shows the latest release tag stripped of its `v` prefix,
             exactly the version downloaded by `--upgrade --develop`
             (REQ-029). The idle-time gate and cache file are bypassed
             (REQ-002); the cache write follows the PyPI outcome only:
             3600 s on success, 86400 s on failure (REQ-031). The call
             always returns normally (A-06).
    @param installed_version {str} Installed version in `x.y.z` format.
    @return {None}
    @satisfies REQ-002 REQ-027 REQ-028 REQ-029 REQ-030 REQ-031 REQ-026
    """
    colors = config.notification_colors()
    check_epoch = time.time()
    pypi_version: str | None = None
    github_version: str | None = None
    pypi_reason = ""
    github_reason = ""
    try:
        pypi_version = _fetch_latest_pypi_version()
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as error:
        pypi_reason = str(error)
        _print_colored(
            colors["error_color"], f"Version check failed @ PyPI: {error}"
        )
    try:
        github_version = _fetch_latest_github_version()
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as error:
        github_reason = str(error)
        _print_colored(
            colors["error_color"], f"Version check failed @ GitHub: {error}"
        )
    print(_format_report_row(_REPORT_LABEL_INSTALLED, installed_version))
    print(
        _format_report_row(
            _REPORT_LABEL_PYPI,
            pypi_version
            if pypi_version is not None
            else _unknown_value(pypi_reason),
        )
    )
    print(
        _format_report_row(
            _REPORT_LABEL_GITHUB,
            github_version
            if github_version is not None
            else _unknown_value(github_reason),
        )
    )
    if pypi_version is not None:
        _write_cache(_cache_path(), check_epoch, _IDLE_DELAY_SUCCESS_SECONDS)
    else:
        _write_cache(_cache_path(), check_epoch, _IDLE_DELAY_FAILURE_SECONDS)

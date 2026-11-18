#!/usr/bin/env python3
## @file version_check.py
# @brief Online new-version check with idle-time cache, executed before CLI
#        argument parsing.
# @details Queries the GitHub releases endpoint with a hardcoded 2 s
#          timeout, throttles repeats through an idle-time JSON cache under
#          `$HOME`, and renders bright green (new version) or bright red
#          (failure) notifications. Success refreshes the cache with a
#          3600 s idle-delay; any failure backs off 86400 s.
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

## @brief GitHub API endpoint returning latest release metadata (REQ-009).
_RELEASES_ENDPOINT = (
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
## @brief ANSI SGR bright-green prefix for availability notes (DES-008).
_ANSI_BRIGHT_GREEN = "\033[92m"
## @brief ANSI SGR bright-red prefix for failure notes (DES-008).
_ANSI_BRIGHT_RED = "\033[91m"
## @brief ANSI SGR reset suffix closing colored notifications.
_ANSI_RESET = "\033[0m"


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


def _fetch_latest_release() -> str:
    """@brief GET the latest release payload and extract `tag_name`.

    @return {str} Latest release tag (e.g. `v1.2.3`).
    @throws {urllib.error.URLError} On HTTP and network failures; includes
            HTTPError carrying the status code (e.g. 429, 503).
    @throws {TimeoutError} On the 2-second timeout expiry.
    @throws {ValueError} On unparsable payload or missing tag_name.
    @satisfies REQ-009 CTN-006
    """
    request = urllib.request.Request(
        _RELEASES_ENDPOINT,
        headers={"Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(
        request, timeout=_HTTP_TIMEOUT_SECONDS
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag_name = payload.get("tag_name")
    if not isinstance(tag_name, str) or not tag_name:
        raise ValueError("release payload misses tag_name")
    return tag_name


def _print_colored(color: str, message: str) -> None:
    """@brief Print a message wrapped in an ANSI color prefix and reset.

    @param color {str} ANSI SGR prefix (bright green or bright red).
    @param message {str} Plain-text message content.
    @return {None}
    @satisfies DES-008
    """
    print(f"{color}{message}{_ANSI_RESET}")


def _report_failure(check_epoch: float, error: BaseException) -> None:
    """@brief Emit the bright-red failure note and write the 86400 s cache.

    @param check_epoch {float} Epoch seconds of the failed attempt.
    @param error {BaseException} Encountered error rendered in the note.
    @return {None}
    @satisfies REQ-014 REQ-015 A-05
    """
    _print_colored(_ANSI_BRIGHT_RED, f"Version check failed: {error}")
    _write_cache(_cache_path(), check_epoch, _IDLE_DELAY_FAILURE_SECONDS)


def run_version_check(installed_version: str, force: bool = False) -> None:
    """@brief Execute the gated (or forced) online version check.

    @details Flow: cache read -> gate evaluation (skipped when `force`) ->
             HTTPS fetch -> version compare -> notify -> cache write.
             Success always refreshes the cache with the 3600 s idle-delay
             (REQ-013, A-04); fetch or parse failures print the bright-red
             error and back off 86400 s (REQ-014, REQ-015, A-05). The call
             always returns normally; callers continue parsing (A-06).
    @param installed_version {str} Installed version in `x.y.z` format.
    @param force {bool} True bypasses the idle-time gate (REQ-002,
           REQ-007).
    @return {None}
    @satisfies REQ-007 REQ-008 REQ-009 REQ-010 REQ-011 REQ-012 REQ-013
               REQ-014 REQ-015
    """
    check_epoch = time.time()
    cache = _read_cache(_cache_path())
    if not force and not _gate_allows_request(cache, check_epoch):
        return
    try:
        latest_tag = _fetch_latest_release()
        available = _parse_version(latest_tag)
        installed = _parse_version(installed_version)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as error:
        _report_failure(check_epoch, error)
        return
    if available > installed:
        _print_colored(
            _ANSI_BRIGHT_GREEN,
            f"New version available: {latest_tag} "
            f"(installed version: {installed_version})",
        )
    _write_cache(_cache_path(), check_epoch, _IDLE_DELAY_SUCCESS_SECONDS)

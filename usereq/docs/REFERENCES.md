# Files Structure
```
.
└── src
    ├── githubtemplateastraluv
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── core.py
    │   ├── management.py
    │   └── version_check.py
    └── templateastraluv
        ├── __init__.py
        ├── __main__.py
        └── core.py
```

# __init__.py | Python | 18L | 0 symbols | 1 imports | 12 comments
> Path: `src/githubtemplateastraluv/__init__.py`

## Imports
```
from githubtemplateastraluv.core import main  # noqa: F401
```


---

# __main__.py | Python | 15L | 0 symbols | 2 imports | 8 comments
> Path: `src/githubtemplateastraluv/__main__.py`

## Imports
```
import sys
from githubtemplateastraluv.core import main
```


---

# core.py | Python | 46L | 1 symbols | 2 imports | 11 comments
> Path: `src/githubtemplateastraluv/core.py`

## Imports
```
import sys
from githubtemplateastraluv import __version__, management, version_check
```

## Definitions

### fn `def main(argv: list[str] | None = None) -> int` (L16-47)
- @brief Execute the gated version check, then dispatch commands.
- @details Dispatch order: `--help` or no arguments -> help screen; `--ver` / `--version` -> version print followed by forced check; then `--upgrade`; then `--uninstall`; unknown input falls back to the help screen. Non-forced invocations execute the gated check before dispatch (REQ-007); forced invocations bypass the gate inside the version branch (REQ-002).
- @param argv {list[str] | None} CLI arguments excluding the program name; None resolves to `sys.argv[1:]`.
- @return {int} Process exit code: 0 on handled dispatch, or the return code of the spawned `uv` subprocess for `--upgrade` `--uninstall`.
- @satisfies REQ-001 REQ-002 REQ-007 A-06

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`main`|fn|pub|16-47|def main(argv: list[str] | None = None) -> int|


---

# management.py | Python | 145L | 9 symbols | 2 imports | 23 comments
> Path: `src/githubtemplateastraluv/management.py`

## Imports
```
import subprocess
import sys
```

## Definitions

- var `PROGRAM_NAME = "githubtemplateastraluv"` (L12)
- @brief Canonical program name used across help text and uv commands.
- var `UPGRADE_COMMAND = [` (L18)
- var `UNINSTALL_COMMAND = ["uv", "tool", "uninstall", "githubtemplateastraluv"]` (L32)
### fn `def is_linux() -> bool` (L38-49)
- @brief Flag column width keeping management help lines aligned.
- @brief Report whether the current operating system is Linux.
- @details `sys.platform` prefix check (covers `linux` and historical `linux2` values); all other platforms take the manual-command branch (A-09).
- @return {bool} True on Linux, False otherwise.
- @satisfies A-09 CTN-009

### fn `def _management_entry(flag: str, description: str) -> str` `priv` (L50-60)
- @brief Render one aligned management-command help line.
- @param flag {str} Command flag (e.g. `--upgrade`).
- @param description {str} Description text placed after the dash.
- @return {str} Line matching the REQ-001 template alignment.
- @satisfies REQ-001

### fn `def build_help_text(version: str) -> str` (L61-98)
- @brief Render the full help screen text (REQ-001 template).
- @details The literal `(x.y.z)` slot of the template receives the installed version (A-01); the `Commands:` section ends with the literal `...` line (A-02).
- @param version {str} Installed version in `x.y.z` format.
- @return {str} Help text without trailing newline; the caller prints it.
- @satisfies REQ-001 A-01 A-02

### fn `def print_help(version: str) -> int` (L99-109)
- @brief Print the full help screen to stdout.
- @param version {str} Installed version in `x.y.z` format.
- @return {int} Always 0.
- @satisfies REQ-001 PRJ-005

### fn `def cmd_upgrade() -> int` (L110-128)
- @brief Reinstall the tool via `uv tool install` on Linux.
- @details On Linux the exact UPGRADE_COMMAND argv executes through subprocess and its exit code propagates. On any other OS no process spawns; a warning plus the manual command print instead (REQ-004).
- @return {int} 0 on manual fallback or successful subprocess; otherwise the `uv` process exit code.
- @satisfies REQ-003 REQ-004 CTN-009

### fn `def cmd_uninstall() -> int` (L129-146)
- @brief Uninstall the tool via `uv tool uninstall` on Linux.
- @details On Linux the exact UNINSTALL_COMMAND argv executes through subprocess and its exit code propagates. On any other OS no process spawns; a warning plus the manual command print instead (REQ-006).
- @return {int} 0 on manual fallback or successful subprocess; otherwise the `uv` process exit code.
- @satisfies REQ-005 REQ-006 CTN-009

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM_NAME`|var|pub|12||
|`UPGRADE_COMMAND`|var|pub|18||
|`UNINSTALL_COMMAND`|var|pub|32||
|`is_linux`|fn|pub|38-49|def is_linux() -> bool|
|`_management_entry`|fn|priv|50-60|def _management_entry(flag: str, description: str) -> str|
|`build_help_text`|fn|pub|61-98|def build_help_text(version: str) -> str|
|`print_help`|fn|pub|99-109|def print_help(version: str) -> int|
|`cmd_upgrade`|fn|pub|110-128|def cmd_upgrade() -> int|
|`cmd_uninstall`|fn|pub|129-146|def cmd_uninstall() -> int|


---

# version_check.py | Python | 230L | 10 symbols | 7 imports | 27 comments
> Path: `src/githubtemplateastraluv/version_check.py`

## Imports
```
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
```

## Definitions

### fn `def _cache_path() -> Path` `priv` (L43-57)
- @brief ANSI SGR reset suffix closing colored notifications.
- @brief Resolve the absolute cache file path from `$HOME`.
- @details Prefers the `HOME` environment variable (CTN-008); falls back to `Path.home()` when unset. Does not create directories.
- @return {Path} Absolute cache file path.
- @satisfies DES-007 CTN-008

### fn `def _read_cache(path: Path) -> dict[str, Any] | None` `priv` (L58-74)
- @brief Load the idle-time cache JSON document.
- @details Returns None when the file is absent, unreadable, unparsable, or not a JSON object; callers treat None as cache-miss.
- @param path {Path} Cache file path.
- @return {dict[str, Any] | None} Parsed cache payload or None.
- @satisfies REQ-008

### fn `def _human_timestamp(epoch_seconds: float) -> str` `priv` (L75-83)
- @brief Format an epoch value as UTC ISO-8601.
- @param epoch_seconds {float} Epoch seconds to render.
- @return {str} Timestamp shaped `YYYY-MM-DDTHH:MM:SSZ`.

### fn `def _write_cache(` `priv` (L84-87)

### fn `def _gate_allows_request(` `priv` (L112-114)
- @brief Persist the four-field idle-time cache document.
- @details Creates missing parent directories. Field names follow A-03.
- @param path {Path} Cache file path.
- @param check_epoch {float} Epoch seconds of the check attempt.
- @param idle_delay_seconds {int} Idle-delay applied after this check.
- @return {None}
- @satisfies REQ-010 REQ-011 DES-007
- @post Cache file holds exactly four fields: last_check_epoch,
last_check_human, idle_time_epoch, idle_time_human.

### fn `def _parse_version(version: str) -> tuple[int, ...]` `priv` (L133-144)
- @brief Evaluate the idle-time request gate.
- @brief Parse a dotted version string into a comparable tuple.
- @details Gate opens on cache-miss (None), non-numeric idle_time_epoch,
or `now_epoch >= idle_time_epoch`; otherwise it stays closed.
- @details Strips one leading `v`/`V` prefix before splitting on dots.
- @param cache {dict[str, Any] | None} Parsed cache payload or None.
- @param now_epoch {float} Current epoch seconds.
- @param version {str} Version or release tag (e.g. `v1.2.3`).
- @return {bool} True when an HTTPS request is permitted.
- @return {tuple[int, ...]} Comparable component tuple.
- @throws {ValueError} If any component is not an integer.
- @satisfies REQ-008

### fn `def _fetch_latest_release() -> str` `priv` (L145-168)
- @brief GET the latest release payload and extract `tag_name`.
- @return {str} Latest release tag (e.g. `v1.2.3`).
- @throws {urllib.error.URLError} On HTTP and network failures; includes HTTPError carrying the status code (e.g. 429, 503).
- @throws {TimeoutError} On the 2-second timeout expiry.
- @throws {ValueError} On unparsable payload or missing tag_name.
- @satisfies REQ-009 CTN-006

### fn `def _print_colored(color: str, message: str) -> None` `priv` (L169-179)
- @brief Print a message wrapped in an ANSI color prefix and reset.
- @param color {str} ANSI SGR prefix (bright green or bright red).
- @param message {str} Plain-text message content.
- @return {None}
- @satisfies DES-008

### fn `def _report_failure(check_epoch: float, error: BaseException) -> None` `priv` (L180-191)
- @brief Emit the bright-red failure note and write the 86400 s cache.
- @param check_epoch {float} Epoch seconds of the failed attempt.
- @param error {BaseException} Encountered error rendered in the note.
- @return {None}
- @satisfies REQ-014 REQ-015 A-05

### fn `def run_version_check(installed_version: str, force: bool = False) -> None` (L192-231)
- @brief Execute the gated (or forced) online version check.
- @details Flow: cache read -> gate evaluation (skipped when `force`) -> HTTPS fetch -> version compare -> notify -> cache write. Success always refreshes the cache with the 3600 s idle-delay (REQ-013, A-04); fetch or parse failures print the bright-red error and back off 86400 s (REQ-014, REQ-015, A-05). The call always returns normally; callers continue parsing (A-06).
- @param installed_version {str} Installed version in `x.y.z` format.
- @param force {bool} True bypasses the idle-time gate (REQ-002, REQ-007).
- @return {None}
- @satisfies REQ-007 REQ-008 REQ-009 REQ-010 REQ-011 REQ-012 REQ-013 REQ-014 REQ-015

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`_cache_path`|fn|priv|43-57|def _cache_path() -> Path|
|`_read_cache`|fn|priv|58-74|def _read_cache(path: Path) -> dict[str, Any] | None|
|`_human_timestamp`|fn|priv|75-83|def _human_timestamp(epoch_seconds: float) -> str|
|`_write_cache`|fn|priv|84-87|def _write_cache(|
|`_gate_allows_request`|fn|priv|112-114|def _gate_allows_request(|
|`_parse_version`|fn|priv|133-144|def _parse_version(version: str) -> tuple[int, ...]|
|`_fetch_latest_release`|fn|priv|145-168|def _fetch_latest_release() -> str|
|`_print_colored`|fn|priv|169-179|def _print_colored(color: str, message: str) -> None|
|`_report_failure`|fn|priv|180-191|def _report_failure(check_epoch: float, error: BaseExcept...|
|`run_version_check`|fn|pub|192-231|def run_version_check(installed_version: str, force: bool...|


---

# __init__.py | Python | 13L | 0 symbols | 1 imports | 7 comments
> Path: `src/templateastraluv/__init__.py`

## Imports
```
from .core import main  # noqa: F401
```


---

# __main__.py | Python | 11L | 0 symbols | 2 imports | 5 comments
> Path: `src/templateastraluv/__main__.py`

## Imports
```
from .core import main
import sys
```


---

# core.py | Python | 15L | 1 symbols | 0 imports | 5 comments
> Path: `src/templateastraluv/core.py`

## Definitions

### fn `def main() -> int` (L7-16)
- @brief Core command dispatch and githubtemplateastraluv CLI runtime orchestration.
- @brief Scaffold dispatcher placeholder of the renamed skeleton copy.
- @details Provides command routing, repository diagnostics, changelog/version workflows, and process wrappers.
- @details Keeps the skeleton schema imports (`from .core import main`) resolvable; the distributed CLI implementation lives in `src/githubtemplateastraluv/`.
- @return {int} Always 0.

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`main`|fn|pub|7-16|def main() -> int|


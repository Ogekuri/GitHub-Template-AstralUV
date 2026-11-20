#!/usr/bin/env python3
## @file colors.py
# @brief Hardcoded notification-color registry embedded as one internal
#        JSON document.
# @details Single source of truth for every notification color (REQ-040):
#          the embedded JSON assigns the new-version and error color
#          tokens (REQ-041) and maps every color token to its ANSI SGR
#          prefix. No CLI option, file, or environment surface can alter
#          these values; parsing happens once at import and cannot fail
#          at runtime.
import json
from typing import Any

## @brief Embedded internal JSON document with the hardcoded color
#        configuration (REQ-040).
# @details Object shape: `notifications` maps `new_version_color` and
#          `error_color` to palette tokens (REQ-041 assignment:
#          `bright_green` / `bright_red`); `palette` maps every color
#          token to its ANSI SGR prefix `ESC [ <code> m`. Escape
#          sequences use the JSON `\u001b` form so the source stays
#          pure printable ASCII. `json.loads` preserves object order, so
#          palette iteration order equals declaration order.
COLOR_CONFIG_JSON = (
    "{\n"
    '  "notifications": {\n'
    '    "new_version_color": "bright_green",\n'
    '    "error_color": "bright_red"\n'
    "  },\n"
    '  "palette": {\n'
    '    "bright_green": "\\u001b[92m",\n'
    '    "bright_red": "\\u001b[91m",\n'
    '    "bright_yellow": "\\u001b[93m",\n'
    '    "bright_blue": "\\u001b[94m",\n'
    '    "bright_magenta": "\\u001b[95m",\n'
    '    "bright_cyan": "\\u001b[96m",\n'
    '    "bright_white": "\\u001b[97m"\n'
    "  }\n"
    "}"
)

## @brief Parsed embedded color configuration (REQ-040).
# @details Shape: `{"notifications": {"new_version_color": str,
#          "error_color": str}, "palette": {token: ANSI SGR prefix}}`.
COLOR_CONFIG: dict[str, Any] = json.loads(COLOR_CONFIG_JSON)

## @brief Ordered palette of color token to ANSI SGR prefix.
# @details Shared registry view of `COLOR_CONFIG["palette"]` consumed by
#          the renderer documentation tables; insertion order equals the
#          embedded JSON declaration order.
PALETTE: dict[str, str] = COLOR_CONFIG["palette"]


def notification_colors() -> dict[str, str]:
    """@brief Resolve the hardcoded ANSI prefixes for notifications.

    @details Selects `PALETTE` entries through the
             `COLOR_CONFIG["notifications"]` assignment (REQ-041);
             hardcoded values need no I/O and cannot fail (REQ-026).
    @return {dict[str, str]} Mapping with `new_version_color` and
            `error_color` ANSI SGR prefix strings.
    @satisfies REQ-026 REQ-040 REQ-041
    """
    assignments = COLOR_CONFIG["notifications"]
    return {
        "new_version_color": PALETTE[assignments["new_version_color"]],
        "error_color": PALETTE[assignments["error_color"]],
    }

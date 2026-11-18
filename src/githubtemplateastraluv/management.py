#!/usr/bin/env python3
## @file management.py
# @brief Management commands of githubtemplateastraluv, isolated from core
#        dispatch logic.
# @details Implements exact help-screen rendering, `uv tool` install and
#          uninstall lifecycle with Linux-only execution gating, and the
#          manual-command fallback for non-Linux platforms.
import subprocess
import sys

## @brief Canonical program name used across help text and uv commands.
PROGRAM_NAME = "githubtemplateastraluv"

## @brief Exact `uv tool install` argv executed on Linux by `--upgrade`.
# @details `' '.join(UPGRADE_COMMAND)` equals the literal string mandated
#          by REQ-003 and is printed verbatim as the manual command on
#          non-Linux platforms (REQ-004). Source resolves from PyPI.
UPGRADE_COMMAND = [
    "uv",
    "tool",
    "install",
    "githubtemplateastraluv",
    "--force",
]

## @brief Exact `uv tool install` argv executed on Linux by
#        `--upgrade --develop` (REQ-032).
# @details `' '.join(UPGRADE_DEVELOP_COMMAND)` equals the literal string
#          mandated by REQ-032 and is printed verbatim as the manual
#          command on non-Linux platforms (REQ-033). Source resolves from
#          the GitHub repository (latest tagged release, any branch).
UPGRADE_DEVELOP_COMMAND = [
    "uv",
    "tool",
    "install",
    "githubtemplateastraluv",
    "--force",
    "--from",
    "git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git",
]

## @brief Exact `uv tool uninstall` argv executed on Linux by `--uninstall`.
# @details `' '.join(UNINSTALL_COMMAND)` equals the literal string mandated
#          by REQ-005 and is printed verbatim as the manual command on
#          non-Linux platforms (REQ-006).
UNINSTALL_COMMAND = ["uv", "tool", "uninstall", "githubtemplateastraluv"]

## @brief Flag column width keeping management help lines aligned.
_FLAG_COLUMN_WIDTH = len("--uninstall")


def is_linux() -> bool:
    """@brief Report whether the current operating system is Linux.

    @details `sys.platform` prefix check (covers `linux` and historical
             `linux2` values); all other platforms take the manual-command
             branch (A-09).
    @return {bool} True on Linux, False otherwise.
    @satisfies A-09 CTN-009
    """
    return sys.platform.startswith("linux")


def _management_entry(flag: str, description: str) -> str:
    """@brief Render one aligned management-command help line.

    @param flag {str} Command flag (e.g. `--upgrade`).
    @param description {str} Description text placed after the dash.
    @return {str} Line matching the REQ-001 template alignment.
    @satisfies REQ-001
    """
    return f"  {flag:<{_FLAG_COLUMN_WIDTH}} - {description}"


def build_help_text(version: str) -> str:
    """@brief Render the full help screen text (REQ-001 template).

    @details The literal `(x.y.z)` slot of the template receives the
             installed version (A-01); the `Commands:` section ends with
             the literal `...` line (A-02).
    @param version {str} Installed version in `x.y.z` format.
    @return {str} Help text without trailing newline; the caller prints it.
    @satisfies REQ-001 A-01 A-02
    """
    entries = [
        _management_entry(
            "--upgrade",
            f"Reinstall {PROGRAM_NAME} on Linux; "
            "print manual command elsewhere.",
        ),
        _management_entry(
            "--uninstall",
            f"Uninstall {PROGRAM_NAME} on Linux; "
            "print manual command elsewhere.",
        ),
        _management_entry("--ver", f"Print the {PROGRAM_NAME} version."),
        _management_entry("--version", f"Print the {PROGRAM_NAME} version."),
        _management_entry(
            "--help",
            "Print the full help screen or the help text of a specific "
            "command.",
        ),
    ]
    header = f"Usage: {PROGRAM_NAME} [command] [options] ({version})"
    lines = (
        [header, "", "Management Commands:"]
        + entries
        + ["", "Commands:", "  ..."]
    )
    return "\n".join(lines)


def print_help(version: str) -> int:
    """@brief Print the full help screen to stdout.

    @param version {str} Installed version in `x.y.z` format.
    @return {int} Always 0.
    @satisfies REQ-001 PRJ-005
    """
    print(build_help_text(version))
    return 0


def cmd_upgrade(develop: bool = False) -> int:
    """@brief Reinstall the tool via `uv tool install` on Linux.

    @details On Linux the exact argv selected by `develop` executes through
             subprocess and its exit code propagates: UPGRADE_COMMAND for
             the PyPI source (REQ-003), UPGRADE_DEVELOP_COMMAND for the
             GitHub development source (REQ-032). On any other OS no
             process spawns; a warning plus the matching manual command
             print instead (REQ-004, REQ-033).
    @param develop {bool} True selects the GitHub development source
           (`--upgrade --develop`); False selects the PyPI source
           (default).
    @return {int} 0 on manual fallback or successful subprocess;
            otherwise the `uv` process exit code.
    @satisfies REQ-003 REQ-004 REQ-032 REQ-033 CTN-009
    """
    command = UPGRADE_DEVELOP_COMMAND if develop else UPGRADE_COMMAND
    if not is_linux():
        print("WARNING: --upgrade executes automatically on Linux only.")
        print(f"Run manually: {' '.join(command)}")
        return 0
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def cmd_uninstall() -> int:
    """@brief Uninstall the tool via `uv tool uninstall` on Linux.

    @details On Linux the exact UNINSTALL_COMMAND argv executes through
             subprocess and its exit code propagates. On any other OS no
             process spawns; a warning plus the manual command print
             instead (REQ-006).
    @return {int} 0 on manual fallback or successful subprocess;
            otherwise the `uv` process exit code.
    @satisfies REQ-005 REQ-006 CTN-009
    """
    if not is_linux():
        print("WARNING: --uninstall executes automatically on Linux only.")
        print(f"Run manually: {' '.join(UNINSTALL_COMMAND)}")
        return 0
    completed = subprocess.run(UNINSTALL_COMMAND, check=False)
    return int(completed.returncode)

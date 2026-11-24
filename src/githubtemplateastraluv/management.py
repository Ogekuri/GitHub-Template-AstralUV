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

## @brief Exact `uv tool upgrade` argv executed on Linux by
#        `--upgrade` without `--force` (REQ-003).
# @details `' '.join(UPGRADE_COMMAND)` equals the literal string mandated
#          by REQ-003 and is printed verbatim as the manual command on
#          non-Linux platforms (REQ-004). Source resolves from PyPI; the
#          standard upgrade applies no forcing option (REQ-037).
UPGRADE_COMMAND = [
    "uv",
    "tool",
    "upgrade",
    "githubtemplateastraluv",
]

## @brief Exact `uv tool install` argv executed on Linux by
#        `--upgrade --force` (REQ-035).
# @details `' '.join(UPGRADE_FORCE_COMMAND)` equals the literal string
#          mandated by REQ-035 and is printed verbatim as the manual
#          command on non-Linux platforms (REQ-004). The forcing options
#          force the full re-download and complete reinstallation of the
#          package from PyPI (REQ-037).
UPGRADE_FORCE_COMMAND = [
    "uv",
    "tool",
    "install",
    "githubtemplateastraluv",
    "--force",
    "--reinstall",
    "--refresh",
]

## @brief Exact upgrading `uv tool install` argv executed on Linux by
#        `--upgrade --develop` without `--force` (REQ-032).
# @details `' '.join(UPGRADE_DEVELOP_COMMAND)` equals the literal string
#          mandated by REQ-032 and is printed verbatim as the manual
#          command on non-Linux platforms (REQ-033). Source resolves from
#          the GitHub `develop` branch head (`@develop` ref);
#          `--reinstall` replaces the already-installed tool because
#          `uv tool upgrade` rejects `--from`; no `--force` applies
#          (REQ-037).
UPGRADE_DEVELOP_COMMAND = [
    "uv",
    "tool",
    "install",
    "githubtemplateastraluv",
    "--reinstall",
    "--from",
    "git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git@develop",
]

## @brief Exact `uv tool install` argv executed on Linux by
#        `--upgrade --develop --force` (REQ-036).
# @details `' '.join(UPGRADE_DEVELOP_FORCE_COMMAND)` equals the literal
#          string mandated by REQ-036 and is printed verbatim as the
#          manual command on non-Linux platforms (REQ-033). The forcing
#          options force the full re-download and complete reinstallation
#          from the GitHub `develop` branch source (REQ-037).
UPGRADE_DEVELOP_FORCE_COMMAND = [
    "uv",
    "tool",
    "install",
    "githubtemplateastraluv",
    "--force",
    "--reinstall",
    "--refresh",
    "--from",
    "git+https://github.com/Ogekuri/GitHub-Template-AstralUV.git@develop",
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
    """@brief Render one aligned help-screen entry line.

    @param flag {str} Command or option flag (e.g. `--upgrade`).
    @param description {str} Description text placed after the dash.
    @return {str} Line matching the REQ-001 template alignment.
    @satisfies REQ-001 REQ-039
    """
    return f"  {flag:<{_FLAG_COLUMN_WIDTH}} - {description}"


def _upgrade_command(develop: bool, force: bool) -> list[str]:
    """@brief Select the exact upgrade argv for the requested variant.

    @details Mapping mandated by the SRS: `(False, False)` ->
             UPGRADE_COMMAND (REQ-003), `(False, True)` ->
             UPGRADE_FORCE_COMMAND (REQ-035), `(True, False)` ->
             UPGRADE_DEVELOP_COMMAND (REQ-032), `(True, True)` ->
             UPGRADE_DEVELOP_FORCE_COMMAND (REQ-036). Forcing options are
             applied only when `force` is True; non-forced variants
             upgrade without `--force` (REQ-037).
    @param develop {bool} True selects the GitHub development source.
    @param force {bool} True selects the forced reinstallation variant.
    @return {list[str]} Exact argv of the requested upgrade variant.
    @satisfies REQ-003 REQ-032 REQ-035 REQ-036 REQ-037
    """
    if develop:
        return (
            UPGRADE_DEVELOP_FORCE_COMMAND if force
            else UPGRADE_DEVELOP_COMMAND
        )
    return UPGRADE_FORCE_COMMAND if force else UPGRADE_COMMAND


def build_help_text(version: str) -> str:
    """@brief Render the full help screen text (REQ-001 template).

    @details The literal `(x.y.z)` slot of the template receives the
             installed version (A-01); the `Management Commands:` section
             lists every management command, the `Configuration Commands:`
             section lists every configuration command (REQ-039), and the
             `Options:` section documents the `--develop` and `--force`
             modifiers of `--upgrade`.
    @param version {str} Installed version in `x.y.z` format.
    @return {str} Help text without trailing newline; the caller prints it.
    @satisfies REQ-001 REQ-039 A-01 A-02
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
        _management_entry("--help", "Print the full help screen."),
    ]
    configuration_entries = [
        _management_entry(
            "--get",
            "Print the value at Path as one JSON document.",
        ),
        _management_entry(
            "--set",
            "Parse Value into the schema type and persist it at Path.",
        ),
        _management_entry(
            "--unset",
            "Restore Path to its schema default and persist atomically.",
        ),
        _management_entry(
            "--print",
            "Print current values as a box-drawing tree, "
            "whole schema or at Path.",
        ),
        _management_entry(
            "--info",
            "Print parameter documentation with defaults, "
            "constraints, and examples.",
        ),
        _management_entry(
            "--print-raw",
            "Print the exact bytes of the configuration JSON file.",
        ),
    ]
    option_entries = [
        _management_entry(
            "--develop",
            "With --upgrade: install from the GitHub development source.",
        ),
        _management_entry(
            "--force",
            "With --upgrade: force full re-download and reinstallation.",
        ),
    ]
    header = f"Usage: {PROGRAM_NAME} [command] [options] ({version})"
    lines = (
        [header, "", "Management Commands:"]
        + entries
        + ["", "Configuration Commands:"]
        + configuration_entries
        + ["", "Options:"]
        + option_entries
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


def cmd_upgrade(develop: bool = False, force: bool = False) -> int:
    """@brief Upgrade the tool via `uv` on Linux.

    @details On Linux the exact argv selected by `develop` and `force`
             executes through subprocess and its exit code propagates:
             UPGRADE_COMMAND for the PyPI upgrade (REQ-003),
             UPGRADE_FORCE_COMMAND for the forced PyPI reinstallation
             (REQ-035), UPGRADE_DEVELOP_COMMAND for the GitHub
             development reinstall (REQ-032), and
             UPGRADE_DEVELOP_FORCE_COMMAND for the forced development
             reinstallation (REQ-036); forcing options apply only when
             `force` is True (REQ-037). On any other OS no process spawns;
             a warning plus the matching manual command print instead
             (REQ-004, REQ-033).
    @param develop {bool} True selects the GitHub development source
           (`--upgrade --develop`); False selects the PyPI source
           (default).
    @param force {bool} True selects the forced full re-download and
           reinstallation variant (`--upgrade --force`, REQ-037);
           False executes the standard process without any forcing
           option.
    @return {int} 0 on manual fallback or successful subprocess;
            otherwise the `uv` process exit code.
    @satisfies REQ-003 REQ-004 REQ-032 REQ-033 REQ-035 REQ-036 REQ-037
               CTN-009
    """
    command = _upgrade_command(develop, force)
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

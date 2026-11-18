#!/usr/bin/env python3
## @file core.py
# @brief Core command dispatch and githubtemplateastraluv CLI runtime
#        orchestration.
# @details Runs the automatic online version check before argument dispatch,
#          then routes management commands to dedicated handlers and
#          propagates exit codes to the process boundary.
import sys

from githubtemplateastraluv import __version__, management, version_check
# `__version__` is the single version source (package __init__, skeleton
# schema); mirrored by pyproject.toml, scripts/templateastraluv.sh,
# README.md, and uv.lock per .g.conf ver_rules.


def main(argv: list[str] | None = None) -> int:
    """@brief Execute the gated version check, then dispatch commands.

    @details Dispatch order: `--help` or no arguments -> help screen;
             `--ver` / `--version` -> version print followed by forced
             check; then `--upgrade`; then `--uninstall`; unknown input
             falls back to the help screen. Non-forced invocations execute
             the gated check before dispatch (REQ-007); forced invocations
             bypass the gate inside the version branch (REQ-002).
    @param argv {list[str] | None} CLI arguments excluding the program
           name; None resolves to `sys.argv[1:]`.
    @return {int} Process exit code: 0 on handled dispatch, or the return
            code of the spawned `uv` subprocess for `--upgrade` /
            `--uninstall`.
    @satisfies REQ-001 REQ-002 REQ-007 A-06
    """
    args = list(sys.argv[1:]) if argv is None else list(argv)
    forced = "--ver" in args or "--version" in args
    if not forced:
        version_check.run_version_check(__version__, False)
    if not args or ("--help" in args and not forced):
        return management.print_help(__version__)
    if forced:
        print(__version__)
        version_check.run_version_check(__version__, True)
        return 0
    if "--upgrade" in args:
        return management.cmd_upgrade()
    if "--uninstall" in args:
        return management.cmd_uninstall()
    return management.print_help(__version__)

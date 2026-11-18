#!/usr/bin/env python3
## @file core.py
# @brief Core command dispatch and githubtemplateastraluv CLI runtime
#        orchestration.
# @details Runs the automatic online version check before argument dispatch,
#          then routes management and configuration commands to dedicated
#          handlers and propagates exit codes to the process boundary.
import sys

from githubtemplateastraluv import (
    __version__,
    config,
    config_render,
    management,
    version_check,
)
# `__version__` is the single version source (package __init__, skeleton
# schema); mirrored by pyproject.toml, scripts/templateastraluv.sh,
# README.md, and uv.lock per .g.conf ver_rules.


def main(argv: list[str] | None = None) -> int:
    """@brief Execute the gated version check, then dispatch commands.

    @details Dispatch order: `--help` or no arguments -> help screen;
             `--ver` / `--version` -> aligned three-row version report
             fetching PyPI and GitHub with the gate bypassed (REQ-002,
             REQ-027..REQ-031); then `--upgrade`, optionally with the
             `--develop` source modifier selecting the GitHub
             development source (REQ-032..REQ-034); then `--uninstall`;
             then the additive configuration CLI commands `--get`,
             `--set`, `--unset`, `--print-raw`, `--print`, `--info`
             (PRJ-006); unknown input falls back to the help screen.
             Non-forced invocations execute the gated PyPI check before
             dispatch (REQ-007). Existing management dispatch and
             observable behavior are unchanged by the configuration
             branches (REQ-016..REQ-021).
    @param argv {list[str] | None} CLI arguments excluding the program
           name; None resolves to `sys.argv[1:]`.
    @return {int} Process exit code: 0 on handled dispatch, or the return
            code of the spawned `uv` subprocess for `--upgrade` /
            `--uninstall`, or 1 for configuration CLI failures
            (REQ-023).
    @satisfies REQ-001 REQ-002 REQ-007 REQ-016 REQ-017 REQ-018 REQ-019
               REQ-020 REQ-021 REQ-027 REQ-028 REQ-029 REQ-030 REQ-031
               REQ-032 REQ-033 REQ-034 A-06 PRJ-006
    """
    args = list(sys.argv[1:]) if argv is None else list(argv)
    forced = "--ver" in args or "--version" in args
    if not forced:
        version_check.run_version_check(__version__, False)
    if not args or ("--help" in args and not forced):
        return management.print_help(__version__)
    if forced:
        version_check.run_version_report(__version__)
        return 0
    if "--upgrade" in args:
        develop = "--develop" in args
        return management.cmd_upgrade(develop)
    if "--uninstall" in args:
        return management.cmd_uninstall()
    if "--get" in args:
        return config.handle_get(args)
    if "--set" in args:
        return config.handle_set(args)
    if "--unset" in args:
        return config.handle_unset(args)
    if "--print-raw" in args:
        return config.handle_print_raw(args)
    if "--print" in args:
        return config_render.handle_print(args)
    if "--info" in args:
        return config_render.handle_info(args)
    return management.print_help(__version__)

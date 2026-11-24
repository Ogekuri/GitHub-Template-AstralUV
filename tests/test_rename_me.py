#!/usr/bin/env python3
## @file test_rename_me.py
# @brief HDT unit suite (Generator mode) covering TST-033 and TST-034 for
#        the one-shot template instantiation script `scripts/rename-me.sh`
#        (PRJ-010, DES-061..DES-069).
# @details HDT static-analysis artifact (section 7.1):
#          - UUTs and levels: L1 = scripts/rename-me.sh executed
#            end-to-end as one script-level unit (bash orchestration of
#            find/grep/sed/mv/rm; no internal functions under `src/`
#            exist to level further).
#          - External dependencies isolated: filesystem (the UUT operates
#            only on a disposable working-tree copy under `temp/`; the
#            tracked repository tree is never mutated), process spawn
#            (`subprocess.run` with captured stdout/stderr), network
#            (none; the script invokes no network tooling), wall clock
#            (unneeded; the per-run sandbox name uses the worker pid).
#          - Determinism: fixed parameter vectors whose target values
#            carry no source substring; the template copy skips `.git`,
#            `temp`, `.venv`, caches, build outputs, and bytecode
#            directories, mirroring the script's own prune contract.
#          - Execution plan (dev signal): `uv run pytest
#            tests/test_rename_me.py -q` from the project root; the full
#            suite command `uv run pytest -q` keeps this module alongside
#            the L0..L2 CLI suites.
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
SCRIPT_PATH: Path = REPO_ROOT / "scripts" / "rename-me.sh"
TEMP_ROOT: Path = REPO_ROOT / "temp"

## @brief Byte-exact source-string oracle duplicated from the SRS
#         rename-instantiation mapping (TST-034) to keep the assertion set
#         independent from the implementation constants.
SOURCE_STRINGS: tuple[str, ...] = (
    "Francesco Rolando",
    "GitHub template for Astral-UV app",
    "githubtemplateastraluv",
    "templateastraluv",
    "Ogekuri",
    "GitHub-Template-AstralUV",
)

## @brief Optional-parameter source strings preserved on omission (DES-063).
OPTIONAL_SOURCE_STRINGS: tuple[str, ...] = (
    "Francesco Rolando",
    "Ogekuri",
)

## @brief Target identity values of the complete-rename vector; none of
#         them contains any source string as a substring.
RENAMED_DESCRIPTION = "Deep space telemetry toolkit"
RENAMED_PROGRAM = "novaprobe"
RENAMED_SHORTNAME = "nova"
RENAMED_REPOSITORY = "Nova-Probe-Repo"
RENAMED_PUBLISHNAME = "novaprobe-pypi"
RENAMED_AUTHOR = "Mario Rossi"
RENAMED_OWNER = "TestOwner"

## @brief Complete rename parameter vector (TST-033): all seven parameters.
COMPLETE_RENAME_PARAMETERS: tuple[str, ...] = (
    "--description", RENAMED_DESCRIPTION,
    "--program", RENAMED_PROGRAM,
    "--shortname", RENAMED_SHORTNAME,
    "--repository", RENAMED_REPOSITORY,
    "--publishname", RENAMED_PUBLISHNAME,
    "--author", RENAMED_AUTHOR,
    "--owner", RENAMED_OWNER,
)

## @brief Mandatory-only parameter vector (DES-063 boundary): `--author`
#         and `--owner` omitted, so their source strings must survive.
MANDATORY_ONLY_PARAMETERS: tuple[str, ...] = (
    "--description", RENAMED_DESCRIPTION,
    "--program", RENAMED_PROGRAM,
    "--shortname", RENAMED_SHORTNAME,
    "--repository", RENAMED_REPOSITORY,
    "--publishname", RENAMED_PUBLISHNAME,
)

## @brief Copy filter mirroring the script's prune contract: the sandbox
#         copy is a plain tree without `.git` (DES-061) without generated
#         cache or virtual-environment directories; the tracked `dist/`
#         artifacts stay included because their filenames carry the
#         program name (DES-066) and `temp/` is the recursion guard.
COPY_IGNORE_PATTERNS = shutil.ignore_patterns(
    ".git",
    "temp",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
)


def _copy_template(destination: Path) -> None:
    """@brief Copy the template working tree into the sandbox destination.

    @details Mirrors every tracked and untracked non-ignored working-tree
             file (including the tracked `dist/` release artifacts whose
             filenames carry the program name) while skipping `.git`, the
             `temp/` scratch root (recursion guard), and generated cache
             or virtual-environment directories; the sandbox copy is a
             plain tree without `.git`, which the script must support
             (DES-061).
    @param destination {Path} Sandbox copy root (inside `temp/`).
    @return {None}
    """
    shutil.copytree(REPO_ROOT, destination, ignore=COPY_IGNORE_PATTERNS)


def _run_rename_script(
    script_path: Path,
    parameters: tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    """@brief Execute one rename script invocation with captured streams.

    @param script_path {Path} Absolute path of the script to execute.
    @param parameters {tuple[str, ...]} Complete CLI parameter vector.
    @return {CompletedProcess[str]} Completed process with decoded
            stdout/stderr; the caller asserts on `returncode`.
    """
    return subprocess.run(
        ["bash", str(script_path), *parameters],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )


def _is_text_content(content: bytes) -> bool:
    """@brief Report whether raw file bytes are scannable text.

    @details Applies the same binary exclusion contract as the script's
             `grep -I` filter (TST-034): NUL bytes in the leading 8 KiB or
             a failing strict UTF-8 decode classify the payload as binary,
             so compressed distribution archives (sdist tarball, wheel
             zip) are excluded from content scanning while every tracked
             text file stays covered.
    @param content {bytes} Raw file bytes.
    @return {bool} True when the payload is scannable text.
    """
    if b"\x00" in content[:8192]:
        return False
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _assert_no_source_strings(
    copy_root: Path,
    sources: tuple[str, ...] = SOURCE_STRINGS,
) -> None:
    """@brief Assert the TST-034 residual-free contract over the copy.

    @details Walks the whole sandbox tree: every file and directory name
             must avoid all given source strings, and every text-file
             content (binary archives excluded per TST-034) must avoid
             them byte-wise; violations fail with the offending path and
             string.
    @param copy_root {Path} Sandbox copy root to scan.
    @param sources {tuple[str, ...]} Source strings that must be absent.
    @return {None}
    @throws {AssertionError} On any surviving source-string occurrence.
    """
    encoded_sources = [source.encode("utf-8") for source in sources]
    for dirpath, dirnames, filenames in os.walk(copy_root):
        for name in dirnames + filenames:
            for source in sources:
                assert source not in name, (
                    f"source string {source!r} survives in path: "
                    f"{Path(dirpath) / name}"
                )
        for filename in filenames:
            file_path = Path(dirpath) / filename
            content = file_path.read_bytes()
            if not _is_text_content(content):
                continue
            for encoded in encoded_sources:
                assert encoded not in content, (
                    f"source string {encoded.decode('utf-8')!r} survives "
                    f"in file: {file_path}"
                )


def test_rename_me_complete_rename_removes_all_source_strings() -> None:
    """@brief TST-033/TST-034 happy path: full seven-parameter rename.

    @details Copies the template working tree into `temp/`, executes the
             copied script with all mandatory and optional parameters
             (AAA arrange/act), and asserts exit status 0 with captured
             diagnostics on failure, self-removal of the copied script
             (DES-069), the TST-034 residual-free contract over names and
             text contents, and the positive instantiation of the new
             identity across the renamed launcher, package, and skeleton
             directories (DES-066).
    @return {None}
    """
    work_root = TEMP_ROOT / f"rename-me-complete-{os.getpid()}"
    copy_root = work_root / "template-copy"
    try:
        _copy_template(copy_root)
        result = _run_rename_script(
            copy_root / "scripts" / "rename-me.sh",
            COMPLETE_RENAME_PARAMETERS,
        )
        assert result.returncode == 0, (
            "expected exit 0; "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert not (copy_root / "scripts" / "rename-me.sh").exists(), (
            "the rename script must remove itself after full success "
            "(DES-069)"
        )
        _assert_no_source_strings(copy_root)
        assert (copy_root / "src" / RENAMED_PROGRAM / "__main__.py").is_file()
        assert (copy_root / "scripts" / f"{RENAMED_SHORTNAME}.sh").is_file()
        assert (copy_root / "src" / RENAMED_SHORTNAME / "core.py").is_file()
    finally:
        shutil.rmtree(work_root, ignore_errors=True)


def test_rename_me_optional_parameters_default_preserves_author_and_owner() -> None:
    """@brief DES-063 boundary: omitted optional parameters keep sources.

    @details Runs the copied script with the mandatory-only vector and
             asserts exit status 0, absence of the mandatory-source
             strings across names and text contents, and byte-presence of
             `Francesco Rolando` and `Ogekuri` inside the copied
             `pyproject.toml` (omission preserves both source strings).
    @return {None}
    """
    work_root = TEMP_ROOT / f"rename-me-mandatory-only-{os.getpid()}"
    copy_root = work_root / "template-copy"
    mandatory_sources = tuple(
        source for source in SOURCE_STRINGS
        if source not in OPTIONAL_SOURCE_STRINGS
    )
    try:
        _copy_template(copy_root)
        result = _run_rename_script(
            copy_root / "scripts" / "rename-me.sh",
            MANDATORY_ONLY_PARAMETERS,
        )
        assert result.returncode == 0, (
            "expected exit 0; "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        _assert_no_source_strings(copy_root, mandatory_sources)
        pyproject_bytes = (copy_root / "pyproject.toml").read_bytes()
        for source in OPTIONAL_SOURCE_STRINGS:
            assert source.encode("utf-8") in pyproject_bytes, (
                f"omitted optional source string must survive: {source!r}"
            )
    finally:
        shutil.rmtree(work_root, ignore_errors=True)


def test_rename_me_missing_mandatory_parameter_terminates_non_zero() -> None:
    """@brief DES-062 error boundary: incomplete usage aborts pre-mutation.

    @details Invokes the tracked script with only `--description` and
             asserts a non-zero exit with a non-empty stderr diagnostic
             (usage contract), plus that the script file still exists:
             parameter validation precedes every mutation, so no
             self-removal and no repository mutation can occur (DES-068).
    @return {None}
    """
    result = _run_rename_script(
        SCRIPT_PATH,
        ("--description", RENAMED_DESCRIPTION),
    )
    assert result.returncode != 0, (
        "incomplete usage must terminate non-zero (DES-062)"
    )
    assert result.stderr.strip() != "", (
        "the failure must carry a stderr diagnostic (DES-062)"
    )
    assert SCRIPT_PATH.is_file(), (
        "a usage failure must not remove the script (DES-068)"
    )

#!/usr/bin/env python3
## @file config.py
# @brief Configuration subsystem: canonical schema, strict validation,
#        atomic JSON persistence, path resolution, and CLI handlers.
# @details Single source of truth driving parsing, validation, defaults,
#          path discovery, and configuration output (DES-010). State
#          persists as JSON at `$HOME/.config/githubtemplateastraluv/
#          config.json`. Version-check transport parameters stay hardcoded
#          (CTN-008) and are not part of the schema. Handlers emit valid
#          output on stdout only, report failures on stderr with exit
#          status 1, and never mutate state on rejected operations
#          (REQ-023).
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

## @brief Ordered mapping of Selection enum token to ANSI SGR prefix.
# @details Insertion order defines enum display order (REQ-025).
COLOR_ANSI: dict[str, str] = {
    "bright_green": "\033[92m",
    "bright_red": "\033[91m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
}

## @brief Ordered Selection enum tokens shared by both parameters (REQ-025).
_SELECTION_ENUM: tuple[str, ...] = tuple(COLOR_ANSI)

## @brief Global configuration directory segments relative to `$HOME`.
_CONFIG_DIR_SEGMENTS: tuple[str, ...] = (
    ".config",
    "githubtemplateastraluv",
)

## @brief Global configuration JSON file name.
_CONFIG_FILE_NAME = "config.json"


@dataclass(frozen=True)
class ParamSpec:
    """@brief Immutable schema descriptor of one configuration parameter.

    @details `token` equals the CLI path token byte for byte (REQ-022);
             drives parsing, validation, defaults, display, and
             documentation (DES-010).
    """
    ## @brief Canonical CLI path token of the parameter.
    token: str
    ## @brief Schema type label rendered in `--info` headings.
    type_label: str
    ## @brief Concise English description rendered in `--info`.
    description: str
    ## @brief Schema default value restored by `--unset` (REQ-018).
    default: str
    ## @brief Ordered allowed values for Selection parameters (REQ-025).
    enum: tuple[str, ...]

    @property
    def constraints(self) -> str:
        """@brief Constraints fragment rendered after the type label.

        @return {str} Constraint summary, e.g. `7 allowed values`.
        """
        return f"{len(self.enum)} allowed values"


@dataclass(frozen=True)
class SectionSpec:
    """@brief Immutable schema descriptor of one fixed-schema section.

    @details Fixed-schema dictionary branch; whole-section `--set`
             replaces the branch with a schema-compatible JSON object and
             `--unset` restores all parameter defaults (REQ-018).
    """
    ## @brief Canonical CLI path token of the section.
    token: str
    ## @brief Concise English description rendered in `--print`/`--info`.
    description: str
    ## @brief Ordered parameter descriptors of the section.
    params: tuple[ParamSpec, ...]

    def param(self, token: str) -> ParamSpec | None:
        """@brief Look up a parameter descriptor by canonical token.

        @param token {str} Exact parameter path token (case-sensitive).
        @return {ParamSpec | None} Matching descriptor; None if absent.
        """
        for candidate in self.params:
            if candidate.token == token:
                return candidate
        return None


## @brief Canonical configuration schema (DES-010, REQ-024).
# @details Insertion order defines canonical display order.
SCHEMA: tuple[SectionSpec, ...] = (
    SectionSpec(
        token="Notifications",
        description="Version-check notification appearance.",
        params=(
            ParamSpec(
                token="new_version_color",
                type_label="Selection",
                description="ANSI color of the new-version availability note.",
                default="bright_green",
                enum=_SELECTION_ENUM,
            ),
            ParamSpec(
                token="error_color",
                type_label="Selection",
                description="ANSI color of the version-check failure note.",
                default="bright_red",
                enum=_SELECTION_ENUM,
            ),
        ),
    ),
)

## @brief Schema token to SectionSpec index for O(1) path resolution.
_SECTIONS_BY_TOKEN: dict[str, SectionSpec] = {
    section.token: section for section in SCHEMA
}


class ConfigError(Exception):
    """@brief Configuration error carrying a user-facing diagnostic.

    @details Raised for invalid paths, values, JSON, validation failures,
             and unrecoverable filesystem conditions; handlers render the
             message on stderr and exit 1 (REQ-023).
    """


def config_path() -> Path:
    """@brief Resolve the absolute global configuration file path.

    @details Prefers the `HOME` environment variable (CTN-008 consistency
             with the version-check cache); falls back to `Path.home()`
             when unset. No project-local configuration layer exists.
    @return {Path} Absolute path of the global configuration JSON file.
    """
    if "HOME" in os.environ:
        base = Path(os.environ["HOME"])
    else:
        base = Path.home()
    return base.joinpath(*_CONFIG_DIR_SEGMENTS, _CONFIG_FILE_NAME)


def default_config() -> dict[str, dict[str, str]]:
    """@brief Build the schema-default configuration payload.

    @return {dict[str, dict[str, str]]} Section token to parameter token
            to default value, in canonical schema order.
    """
    return {
        section.token: {param.token: param.default for param in section.params}
        for section in SCHEMA
    }


def validate_config(payload: Any) -> None:
    """@brief Validate a complete configuration against the schema.

    @details Strict validation: JSON object root, exact section key set,
             exact parameter key set per section, and Selection values
             restricted to the schema enum (REQ-025). Raises without
             mutation; callers reject the operation on error.
    @param payload {Any} Parsed JSON configuration payload.
    @return {None}
    @throws {ConfigError} On root-type, section-key, parameter-key, or
            enum-membership mismatch; message names the offending path.
    """
    if not isinstance(payload, dict):
        raise ConfigError(
            "configuration root must be a JSON object; "
            f"got {type(payload).__name__}"
        )
    expected_sections = set(_SECTIONS_BY_TOKEN)
    actual_sections = set(payload)
    unknown = sorted(actual_sections - expected_sections)
    missing = sorted(expected_sections - actual_sections)
    if unknown or missing:
        raise ConfigError(
            "configuration sections mismatch"
            + (f"; unknown sections: {unknown}" if unknown else "")
            + (f"; missing sections: {missing}" if missing else "")
        )
    for section in SCHEMA:
        branch = payload[section.token]
        if not isinstance(branch, dict):
            raise ConfigError(
                f"section {section.token} must be a JSON object; "
                f"got {type(branch).__name__}"
            )
        expected_params = {param.token for param in section.params}
        actual_params = set(branch)
        unknown_params = sorted(actual_params - expected_params)
        missing_params = sorted(expected_params - actual_params)
        if unknown_params or missing_params:
            raise ConfigError(
                f"section {section.token} parameters mismatch"
                + (f"; unknown: {unknown_params}" if unknown_params else "")
                + (f"; missing: {missing_params}" if missing_params else "")
            )
        for param in section.params:
            value = branch[param.token]
            if not isinstance(value, str) or value not in param.enum:
                raise ConfigError(
                    f"invalid value for {section.token}:{param.token}: "
                    f"{value!r}; allowed values: {', '.join(param.enum)}"
                )


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """@brief Persist a validated payload atomically (DES-014).

    @details Writes a same-directory temporary file, flushes and fsyncs
             it, preserves the prior target file mode, atomically replaces
             the target with `os.replace`, and fsyncs the parent
             directory where the platform supports it. The prior valid
             file survives any failure before the replace; on failure the
             temporary file is removed.
    @param path {Path} Target configuration file path.
    @param payload {dict[str, Any]} Schema-validated payload to store.
    @return {None}
    @throws {ConfigError} When directory creation or the write/replace
            sequence fails; the original file stays untouched.
    @post On success the file holds exactly the serialized payload with
          two-space indentation and a trailing newline.
    """
    text = json.dumps(payload, indent=2) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        prior_mode = (
            path.stat().st_mode & 0o777 if path.exists() else None
        )
        descriptor, temporary_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=path.name + ".",
            suffix=".tmp",
        )
    except OSError as error:
        raise ConfigError(f"cannot prepare configuration write: {error}")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if prior_mode is not None:
            os.chmod(temporary_name, prior_mode)
        os.replace(temporary_name, path)
    except OSError as error:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise ConfigError(f"cannot persist configuration: {error}")
    try:
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:
        pass


def ensure_bootstrapped() -> None:
    """@brief Create missing directories and initialize missing defaults.

    @details Applicable configuration commands call this before executing
             (REQ-024 storage lifecycle). Never overwrites an existing
             file, valid or not; strict loaders surface invalid files as
             errors.
    @return {None}
    @throws {ConfigError} When directories cannot be created or the
            default file cannot be written.
    """
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            atomic_write_json(path, default_config())
    except ConfigError:
        raise
    except OSError as error:
        raise ConfigError(f"cannot initialize configuration: {error}")


def load_strict() -> dict[str, dict[str, str]]:
    """@brief Load and strictly validate the global configuration.

    @details Reads the file selected by `config_path`, parses JSON, and
             applies `validate_config`; every failure raises instead of
             partially succeeding (REQ-022, REQ-023).
    @return {dict[str, dict[str, str]]} Validated configuration payload.
    @throws {ConfigError} When the file is absent, unreadable, malformed
            JSON, or schema-invalid.
    """
    path = config_path()
    if not path.exists():
        raise ConfigError(f"configuration file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"cannot read configuration file: {error}")
    try:
        payload = json.loads(text)
    except ValueError as error:
        raise ConfigError(f"invalid JSON in {path}: {error}")
    validate_config(payload)
    return payload


def load_tolerant() -> dict[str, dict[str, str]]:
    """@brief Load the configuration, falling back to schema defaults.

    @details Used by the version-check notification path (REQ-026): any
             load or validation failure silently selects schema defaults
             so existing non-configuration behavior never breaks and no
             extra output is produced.
    @return {dict[str, dict[str, str]]} Validated payload or defaults.
    """
    try:
        return load_strict()
    except ConfigError:
        return default_config()


def resolve_segments(path: str) -> tuple[str, ...]:
    """@brief Resolve a canonical configuration path against the schema.

    @details Case-sensitive colon-separated tokens (REQ-022). This schema
             defines exactly two depths: `Section` and
             `Section:Parameter`; no array or map parameters exist, so
             deeper segments and reserved operation tokens (`append`,
             `+`, `insert`) are rejected as unknown or misplaced.
    @param path {str} Raw canonical path from the CLI.
    @return {tuple[str, ...]} One or two resolved path tokens.
    @throws {ConfigError} On empty paths, empty tokens, unknown section
            or parameter tokens, and excessive depth; messages list valid
            alternatives.
    """
    if not path:
        raise ConfigError("configuration path must not be empty")
    segments = tuple(path.split(":"))
    if any(segment == "" for segment in segments):
        raise ConfigError(
            f"invalid configuration path {path!r}: empty path token"
        )
    section = _SECTIONS_BY_TOKEN.get(segments[0])
    if section is None:
        raise ConfigError(
            f"unknown configuration section {segments[0]!r} in path "
            f"{path!r}; valid sections: {', '.join(_SECTIONS_BY_TOKEN)}"
        )
    if len(segments) == 1:
        return segments
    if len(segments) == 2:
        if section.param(segments[1]) is None:
            raise ConfigError(
                f"unknown parameter {segments[1]!r} in section "
                f"{section.token}; valid parameters: "
                f"{', '.join(param.token for param in section.params)}"
            )
        return segments
    raise ConfigError(
        f"invalid configuration path {path!r}: the schema defines at "
        "most Section:Parameter; array, map, and index tokens are not "
        "part of this schema"
    )


def get_value(payload: dict[str, Any], segments: tuple[str, ...]) -> Any:
    """@brief Extract the JSON-serializable value at a resolved path.

    @param payload {dict[str, Any]} Validated configuration payload.
    @param segments {tuple[str, ...]} Tokens from `resolve_segments`.
    @return {Any} Section dict copy for depth 1; parameter string for
            depth 2.
    """
    section = payload[segments[0]]
    if len(segments) == 1:
        return dict(section)
    return section[segments[1]]


def parse_value(spec: ParamSpec, raw: str) -> str:
    """@brief Parse a raw CLI operand into the schema type of `spec`.

    @details Selection parameters accept exactly one enum token; JSON
             quoting is not stripped, so quoted input is rejected
             (REQ-017 typed parsing before write).
    @param spec {ParamSpec} Target parameter descriptor.
    @param raw {str} Raw operand string from the CLI.
    @return {str} Validated enum token.
    @throws {ConfigError} When `raw` is not an allowed value; the message
            enumerates valid values.
    """
    if raw not in spec.enum:
        raise ConfigError(
            f"invalid value for {spec.token}: {raw!r}; allowed values: "
            f"{', '.join(spec.enum)}"
        )
    return raw


def set_value(
    payload: dict[str, Any],
    path: str,
    raw: str,
) -> dict[str, dict[str, str]]:
    """@brief Apply a validated `--set` mutation and return the result.

    @details Depth 1 replaces the whole section with a parsed
             schema-compatible JSON object; depth 2 parses the operand
             into the parameter schema type (REQ-017). The resulting
             configuration is validated in full before returning; the
             input payload is never mutated.
    @param payload {dict[str, Any]} Current validated configuration.
    @param path {str} Raw canonical target path.
    @param raw {str} Raw value operand from the CLI.
    @return {dict[str, dict[str, str]]} New validated configuration.
    @throws {ConfigError} On path, JSON, type, enum, or whole-config
            validation failure; no persisted mutation occurs.
    """
    segments = resolve_segments(path)
    updated = {token: dict(branch) for token, branch in payload.items()}
    if len(segments) == 1:
        section = _SECTIONS_BY_TOKEN[segments[0]]
        try:
            replacement = json.loads(raw)
        except ValueError as error:
            raise ConfigError(
                f"value for section {section.token} is not valid JSON: "
                f"{error}"
            )
        updated[section.token] = replacement
    else:
        param = _SECTIONS_BY_TOKEN[segments[0]].param(segments[1])
        if param is None:
            raise ConfigError(f"unknown parameter in path {path!r}")
        updated[segments[0]][param.token] = parse_value(param, raw)
    validate_config(updated)
    return updated


def unset_value(
    payload: dict[str, Any],
    path: str,
) -> dict[str, dict[str, str]]:
    """@brief Apply a `--unset` restore-to-default mutation.

    @details Depth 1 restores all section parameter defaults; depth 2
             restores one parameter default (REQ-018). The resulting
             configuration is validated before returning; the input
             payload is never mutated.
    @param payload {dict[str, Any]} Current validated configuration.
    @param path {str} Raw canonical target path.
    @return {dict[str, dict[str, str]]} New validated configuration.
    @throws {ConfigError} On path resolution or validation failure.
    """
    segments = resolve_segments(path)
    updated = {token: dict(branch) for token, branch in payload.items()}
    defaults = default_config()
    if len(segments) == 1:
        updated[segments[0]] = dict(defaults[segments[0]])
    else:
        updated[segments[0]][segments[1]] = defaults[segments[0]][segments[1]]
    validate_config(updated)
    return updated


def notification_colors() -> dict[str, str]:
    """@brief Resolve configured ANSI color prefixes for notifications.

    @details Tolerant read (REQ-026): any load or validation failure
             selects schema defaults, keeping the version check non-fatal
             and silent about configuration problems.
    @return {dict[str, str]} Mapping with `new_version_color` and
            `error_color` ANSI SGR prefix strings.
    """
    payload = load_tolerant()
    return {
        "new_version_color": COLOR_ANSI[
            payload["Notifications"]["new_version_color"]
        ],
        "error_color": COLOR_ANSI[payload["Notifications"]["error_color"]],
    }


def operand_values(
    args: list[str],
    flag: str,
    minimum: int,
    maximum: int,
) -> list[str]:
    """@brief Extract the operand tokens following one CLI flag.

    @details Operands are every token after the first flag occurrence;
             the count must lie within `[minimum, maximum]`, otherwise a
             usage diagnostic with complete canonical path examples is
             raised (REQ-022).
    @param args {list[str]} CLI argument tokens excluding program name.
    @param flag {str} Exact flag token to locate (e.g. `--set`).
    @param minimum {int} Minimum acceptable operand count.
    @param maximum {int} Maximum acceptable operand count.
    @return {list[str]} Operand tokens in original order.
    @throws {ConfigError} When the operand count is out of range; the
            message embeds schema-valid usage examples.
    """
    index = args.index(flag)
    values = args[index + 1:]
    if not minimum <= len(values) <= maximum:
        expected = (
            f"exactly {minimum}"
            if minimum == maximum
            else f"{minimum} or {maximum}"
        )
        raise ConfigError(
            f"{flag} expects {expected} operand(s); usage examples: "
            + _usage_examples(flag)
        )
    return values


def _usage_examples(flag: str) -> str:
    """@brief Build schema-valid usage examples for one config flag.

    @details Examples always carry complete canonical paths (REQ-022) and
             real schema-valid values.
    @param flag {str} Exact flag token (e.g. `--set`).
    @return {str} Semicolon-separated example command tails.
    """
    if flag == "--get":
        return (
            "'--get Notifications' or "
            "'--get Notifications:new_version_color'"
        )
    if flag == "--set":
        section_example = (
            "--set Notifications "
            '{"new_version_color":"bright_green",'
            '"error_color":"bright_red"}'
        )
        return (
            "'--set Notifications:new_version_color bright_green' or "
            f"'{section_example}'"
        )
    if flag == "--unset":
        return (
            "'--unset Notifications:new_version_color' or "
            "'--unset Notifications'"
        )
    if flag in ("--print", "--info"):
        return (
            f"'{flag}' or '{flag} Notifications' or "
            f"'{flag} Notifications:new_version_color'"
        )
    return f"'{flag}'"


def _fail(error: ConfigError) -> int:
    """@brief Report a configuration failure and yield the exit status.

    @details Diagnostics go to stderr with an `Error:` prefix; stdout
             stays untouched so no partial success output exists
             (REQ-023).
    @param error {ConfigError} Failure carrying the diagnostic message.
    @return {int} Always 1.
    """
    print(f"Error: {error}", file=sys.stderr)
    return 1


def handle_get(args: list[str]) -> int:
    """@brief Execute `--get Path` (REQ-016).

    @details Bootstraps storage, loads strictly, resolves the canonical
             path, and prints the resolved value as one valid JSON
             document on stdout without decoration (JSON-quoted strings,
             objects for sections).
    @param args {list[str]} CLI argument tokens excluding program name.
    @return {int} 0 on success; 1 with a stderr diagnostic on failure.
    """
    try:
        (path,) = operand_values(args, "--get", 1, 1)
        ensure_bootstrapped()
        payload = load_strict()
        value = get_value(payload, resolve_segments(path))
    except ConfigError as error:
        return _fail(error)
    print(json.dumps(value))
    return 0


def handle_set(args: list[str]) -> int:
    """@brief Execute `--set Path Value` (REQ-017, DES-014).

    @details Parses Value into the schema type, validates the entire
             resulting configuration, and persists atomically; success is
             silent and any rejection leaves the stored file untouched.
    @param args {list[str]} CLI argument tokens excluding program name.
    @return {int} 0 on success; 1 with a stderr diagnostic on failure.
    """
    try:
        path, raw = operand_values(args, "--set", 2, 2)
        ensure_bootstrapped()
        payload = load_strict()
        updated = set_value(payload, path, raw)
        atomic_write_json(config_path(), updated)
    except ConfigError as error:
        return _fail(error)
    return 0


def handle_unset(args: list[str]) -> int:
    """@brief Execute `--unset Path` (REQ-018, DES-014).

    @details Restores the targeted parameter or section to schema
             defaults and persists atomically; success is silent.
    @param args {list[str]} CLI argument tokens excluding program name.
    @return {int} 0 on success; 1 with a stderr diagnostic on failure.
    """
    try:
        (path,) = operand_values(args, "--unset", 1, 1)
        ensure_bootstrapped()
        payload = load_strict()
        updated = unset_value(payload, path)
        atomic_write_json(config_path(), updated)
    except ConfigError as error:
        return _fail(error)
    return 0


def handle_print_raw(args: list[str]) -> int:
    """@brief Execute `--print-raw` (REQ-021).

    @details Emits the exact bytes of the global configuration JSON file
             without parsing, reformatting, headings, or trailing text;
             no tree formatting is ever applied (on-disk debugging view).
    @param args {list[str]} CLI argument tokens excluding program name.
    @return {int} 0 on success; 1 with a stderr diagnostic on failure.
    """
    try:
        operand_values(args, "--print-raw", 0, 0)
        ensure_bootstrapped()
        data = config_path().read_bytes()
    except ConfigError as error:
        return _fail(error)
    except OSError as error:
        return _fail(ConfigError(f"cannot read configuration file: {error}"))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    return 0

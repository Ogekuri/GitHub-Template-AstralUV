# Files Structure
```
.
└── src
    ├── githubtemplateastraluv
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── config_render.py
    │   ├── config.py
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

# config.py | Python | 662L | 25 symbols | 7 imports | 53 comments
> Path: `src/githubtemplateastraluv/config.py`

## Imports
```
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
```

## Definitions

### class `class ParamSpec` `@dataclass(frozen=True)` (L47-73)
- @brief Immutable schema descriptor of one configuration parameter.
- @details `token` equals the CLI path token byte for byte (REQ-022); drives parsing, validation, defaults, display, and documentation (DES-010).
- fn `def constraints(self) -> str` (L66-73)
  - @brief Constraints fragment rendered after the type label.
  - @return {str} Constraint summary, e.g. `7 allowed values`.

### class `class SectionSpec` `@dataclass(frozen=True)` (L75-100)
- @brief Immutable schema descriptor of one fixed-schema section.
- @details Fixed-schema dictionary branch; whole-section `--set` replaces the branch with a schema-compatible JSON object and `--unset` restores all parameter defaults (REQ-018).
- fn `def param(self, token: str) -> ParamSpec | None` (L89-100)
  - @brief Ordered parameter descriptors of the section.
  - @brief Look up a parameter descriptor by canonical token.
  - @param token {str} Exact parameter path token (case-sensitive).
  - @return {ParamSpec | None} Matching descriptor; None if absent.

### class `class ConfigError(Exception)` : Exception (L132-140)
- @brief Schema token to SectionSpec index for O(1) path resolution.
- @brief Configuration error carrying a user-facing diagnostic.
- @details Raised for invalid paths, values, JSON, validation failures, and unrecoverable filesystem conditions; handlers render the message on stderr and exit 1 (REQ-023).

### fn `def config_path() -> Path` (L141-155)
- @brief Resolve the absolute global configuration file path.
- @details Prefers the `HOME` environment variable (CTN-008 consistency with the version-check cache); falls back to `Path.home()` when unset. No project-local configuration layer exists.
- @return {Path} Absolute path of the global configuration JSON file.

### fn `def default_config() -> dict[str, dict[str, str]]` (L156-167)
- @brief Build the schema-default configuration payload.
- @return {dict[str, dict[str, str]]} Section token to parameter token to default value, in canonical schema order.

### fn `def validate_config(payload: Any) -> None` (L168-220)
- @brief Validate a complete configuration against the schema.
- @details Strict validation: JSON object root, exact section key set, exact parameter key set per section, and Selection values restricted to the schema enum (REQ-025). Raises without mutation; callers reject the operation on error.
- @param payload {Any} Parsed JSON configuration payload.
- @return {None}
- @throws {ConfigError} On root-type, section-key, parameter-key, or enum-membership mismatch; message names the offending path.

### fn `def atomic_write_json(path: Path, payload: dict[str, Any]) -> None` (L221-274)
- @brief Persist a validated payload atomically (DES-014).
- @details Writes a same-directory temporary file, flushes and fsyncs it, preserves the prior target file mode, atomically replaces the target with `os.replace`, and fsyncs the parent directory where the platform supports it. The prior valid file survives any failure before the replace; on failure the temporary file is removed.
- @param path {Path} Target configuration file path.
- @param payload {dict[str, Any]} Schema-validated payload to store.
- @return {None}
- @throws {ConfigError} When directory creation or the write/replace sequence fails; the original file stays untouched.
- @post On success the file holds exactly the serialized payload with two-space indentation and a trailing newline.

### fn `def ensure_bootstrapped() -> None` (L275-296)
- @brief Create missing directories and initialize missing defaults.
- @details Applicable configuration commands call this before executing (REQ-024 storage lifecycle). Never overwrites an existing file, valid or not; strict loaders surface invalid files as errors.
- @return {None}
- @throws {ConfigError} When directories cannot be created or the default file cannot be written.

### fn `def load_strict() -> dict[str, dict[str, str]]` (L297-321)
- @brief Load and strictly validate the global configuration.
- @details Reads the file selected by `config_path`, parses JSON, and applies `validate_config`; every failure raises instead of partially succeeding (REQ-022, REQ-023).
- @return {dict[str, dict[str, str]]} Validated configuration payload.
- @throws {ConfigError} When the file is absent, unreadable, malformed JSON, or schema-invalid.

### fn `def load_tolerant() -> dict[str, dict[str, str]]` (L322-336)
- @brief Load the configuration, falling back to schema defaults.
- @details Used by the version-check notification path (REQ-026): any load or validation failure silently selects schema defaults so existing non-configuration behavior never breaks and no extra output is produced.
- @return {dict[str, dict[str, str]]} Validated payload or defaults.

### fn `def resolve_segments(path: str) -> tuple[str, ...]` (L337-380)
- @brief Resolve a canonical configuration path against the schema.
- @details Case-sensitive colon-separated tokens (REQ-022). This schema defines exactly two depths: `Section` and `Section:Parameter`; no array or map parameters exist, so deeper segments and reserved operation tokens (`append`, `+`, `insert`) are rejected as unknown or misplaced.
- @param path {str} Raw canonical path from the CLI.
- @return {tuple[str, ...]} One or two resolved path tokens.
- @throws {ConfigError} On empty paths, empty tokens, unknown section or parameter tokens, and excessive depth; messages list valid alternatives.

### fn `def get_value(payload: dict[str, Any], segments: tuple[str, ...]) -> Any` (L381-394)
- @brief Extract the JSON-serializable value at a resolved path.
- @param payload {dict[str, Any]} Validated configuration payload.
- @param segments {tuple[str, ...]} Tokens from `resolve_segments`.
- @return {Any} Section dict copy for depth 1; parameter string for depth 2.

### fn `def parse_value(spec: ParamSpec, raw: str) -> str` (L395-414)
- @brief Parse a raw CLI operand into the schema type of `spec`.
- @details Selection parameters accept exactly one enum token; JSON quoting is not stripped, so quoted input is rejected (REQ-017 typed parsing before write).
- @param spec {ParamSpec} Target parameter descriptor.
- @param raw {str} Raw operand string from the CLI.
- @return {str} Validated enum token.
- @throws {ConfigError} When `raw` is not an allowed value; the message enumerates valid values.

### fn `def set_value(` (L415-418)

### fn `def unset_value(` (L455-457)
- @brief Apply a validated `--set` mutation and return the result.
- @details Depth 1 replaces the whole section with a parsed
schema-compatible JSON object; depth 2 parses the operand
into the parameter schema type (REQ-017). The resulting
configuration is validated in full before returning; the
input payload is never mutated.
- @param payload {dict[str, Any]} Current validated configuration.
- @param path {str} Raw canonical target path.
- @param raw {str} Raw value operand from the CLI.
- @return {dict[str, dict[str, str]]} New validated configuration.
- @throws {ConfigError} On path, JSON, type, enum, or whole-config
validation failure; no persisted mutation occurs.

### fn `def notification_colors() -> dict[str, str]` (L481-498)
- @brief Apply a `--unset` restore-to-default mutation.
- @brief Resolve configured ANSI color prefixes for notifications.
- @details Depth 1 restores all section parameter defaults; depth 2
restores one parameter default (REQ-018). The resulting
configuration is validated before returning; the input
payload is never mutated.
- @details Tolerant read (REQ-026): any load or validation failure selects schema defaults, keeping the version check non-fatal and silent about configuration problems.
- @param payload {dict[str, Any]} Current validated configuration.
- @param path {str} Raw canonical target path.
- @return {dict[str, dict[str, str]]} New validated configuration.
- @return {dict[str, str]} Mapping with `new_version_color` and `error_color` ANSI SGR prefix strings.
- @throws {ConfigError} On path resolution or validation failure.

### fn `def operand_values(` (L499-503)

### fn `def _usage_examples(flag: str) -> str` `priv` (L534-569)
- @brief Extract the operand tokens following one CLI flag.
- @brief Build schema-valid usage examples for one config flag.
- @details Operands are every token after the first flag occurrence;
the count must lie within `[minimum, maximum]`, otherwise a
usage diagnostic with complete canonical path examples is
raised (REQ-022).
- @details Examples always carry complete canonical paths (REQ-022) and real schema-valid values.
- @param args {list[str]} CLI argument tokens excluding program name.
- @param flag {str} Exact flag token to locate (e.g. `--set`).
- @param minimum {int} Minimum acceptable operand count.
- @param maximum {int} Maximum acceptable operand count.
- @param flag {str} Exact flag token (e.g. `--set`).
- @return {list[str]} Operand tokens in original order.
- @return {str} Semicolon-separated example command tails.
- @throws {ConfigError} When the operand count is out of range; the
message embeds schema-valid usage examples.

### fn `def _fail(error: ConfigError) -> int` `priv` (L570-582)
- @brief Report a configuration failure and yield the exit status.
- @details Diagnostics go to stderr with an `Error:` prefix; stdout stays untouched so no partial success output exists (REQ-023).
- @param error {ConfigError} Failure carrying the diagnostic message.
- @return {int} Always 1.

### fn `def handle_get(args: list[str]) -> int` (L583-603)
- @brief Execute `--get Path` (REQ-016).
- @details Bootstraps storage, loads strictly, resolves the canonical path, and prints the resolved value as one valid JSON document on stdout without decoration (JSON-quoted strings, objects for sections).
- @param args {list[str]} CLI argument tokens excluding program name.
- @return {int} 0 on success; 1 with a stderr diagnostic on failure.

### fn `def handle_set(args: list[str]) -> int` (L604-623)
- @brief Execute `--set Path Value` (REQ-017, DES-014).
- @details Parses Value into the schema type, validates the entire resulting configuration, and persists atomically; success is silent and any rejection leaves the stored file untouched.
- @param args {list[str]} CLI argument tokens excluding program name.
- @return {int} 0 on success; 1 with a stderr diagnostic on failure.

### fn `def handle_unset(args: list[str]) -> int` (L624-642)
- @brief Execute `--unset Path` (REQ-018, DES-014).
- @details Restores the targeted parameter or section to schema defaults and persists atomically; success is silent.
- @param args {list[str]} CLI argument tokens excluding program name.
- @return {int} 0 on success; 1 with a stderr diagnostic on failure.

### fn `def handle_print_raw(args: list[str]) -> int` (L643-663)
- @brief Execute `--print-raw` (REQ-021).
- @details Emits the exact bytes of the global configuration JSON file without parsing, reformatting, headings, or trailing text; no tree formatting is ever applied (on-disk debugging view).
- @param args {list[str]} CLI argument tokens excluding program name.
- @return {int} 0 on success; 1 with a stderr diagnostic on failure.

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`ParamSpec`|class|pub|47-73|class ParamSpec|
|`ParamSpec.constraints`|fn|pub|66-73|def constraints(self) -> str|
|`SectionSpec`|class|pub|75-100|class SectionSpec|
|`SectionSpec.param`|fn|pub|89-100|def param(self, token: str) -> ParamSpec | None|
|`ConfigError`|class|pub|132-140|class ConfigError(Exception)|
|`config_path`|fn|pub|141-155|def config_path() -> Path|
|`default_config`|fn|pub|156-167|def default_config() -> dict[str, dict[str, str]]|
|`validate_config`|fn|pub|168-220|def validate_config(payload: Any) -> None|
|`atomic_write_json`|fn|pub|221-274|def atomic_write_json(path: Path, payload: dict[str, Any]...|
|`ensure_bootstrapped`|fn|pub|275-296|def ensure_bootstrapped() -> None|
|`load_strict`|fn|pub|297-321|def load_strict() -> dict[str, dict[str, str]]|
|`load_tolerant`|fn|pub|322-336|def load_tolerant() -> dict[str, dict[str, str]]|
|`resolve_segments`|fn|pub|337-380|def resolve_segments(path: str) -> tuple[str, ...]|
|`get_value`|fn|pub|381-394|def get_value(payload: dict[str, Any], segments: tuple[st...|
|`parse_value`|fn|pub|395-414|def parse_value(spec: ParamSpec, raw: str) -> str|
|`set_value`|fn|pub|415-418|def set_value(|
|`unset_value`|fn|pub|455-457|def unset_value(|
|`notification_colors`|fn|pub|481-498|def notification_colors() -> dict[str, str]|
|`operand_values`|fn|pub|499-503|def operand_values(|
|`_usage_examples`|fn|priv|534-569|def _usage_examples(flag: str) -> str|
|`_fail`|fn|priv|570-582|def _fail(error: ConfigError) -> int|
|`handle_get`|fn|pub|583-603|def handle_get(args: list[str]) -> int|
|`handle_set`|fn|pub|604-623|def handle_set(args: list[str]) -> int|
|`handle_unset`|fn|pub|624-642|def handle_unset(args: list[str]) -> int|
|`handle_print_raw`|fn|pub|643-663|def handle_print_raw(args: list[str]) -> int|


---

# config_render.py | Python | 458L | 18 symbols | 6 imports | 41 comments
> Path: `src/githubtemplateastraluv/config_render.py`

## Imports
```
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any
from githubtemplateastraluv import config
```

## Definitions

### class `class ConfigNode` `@dataclass` (L36-57)
- @brief Typed tree node of one real configuration element.
- @details `kind` distinguishes section/dictionary branches from parameters; `children` holds only real configuration nodes while metadata and tables live in `details` as logical text lines (never rendered with structural edge markers).

### fn `def display_width(text: str) -> int` (L58-76)
- @brief Measure the terminal display width of a string.
- @details Combining characters count zero; East Asian wide and fullwidth characters count two; all others count one.
- @param text {str} Text to measure.
- @return {int} Display width in terminal cells.

### fn `def format_table(headers: list[str], rows: list[list[str]]) -> list[str]` (L77-122)
- @brief Render a rectangular box-drawing table (DES-013).
- @details Column widths derive from the maximum display width of the header and all cells plus one space of padding on each side; every border and row shares identical column boundaries, so `┬`, `┼`, and `┴` align vertically with the `│` separators.
- @param headers {list[str]} Column header cells.
- @param rows {list[list[str]]} Data rows, each with len(headers) cells.
- @return {list[str]} Physical table lines (borders and rows).

### fn `def border(left: str, middle: str, right: str) -> str` (L95-104)
- @brief Render a rectangular box-drawing table (DES-013).
- @brief Render one horizontal border line.
- @details Column widths derive from the maximum display width of the
header and all cells plus one space of padding on each side;
every border and row shares identical column boundaries, so
`┬`, `┼`, and `┴` align vertically with the `│` separators.
- @param headers {list[str]} Column header cells.
- @param rows {list[list[str]]} Data rows, each with len(headers) cells.
- @param left {str} Left corner glyph.
- @param middle {str} Column junction glyph.
- @param right {str} Right corner glyph.
- @return {list[str]} Physical table lines (borders and rows).
- @return {str} Complete border line.

### fn `def data_row(cells: list[str]) -> str` (L105-116)
- @brief Render one padded data row line.
- @param cells {list[str]} Row cells; display-padded to column width.
- @return {str} Complete row line sharing the border boundaries.

### fn `def render_tree(root: ConfigNode) -> str` (L123-151)
- @brief Render a node hierarchy with the canonical prefix algorithm.
- @details Implements the normative traversal: the display root prints without a marker and its attached details use a four-space indent; every real child receives exactly one `├── `/`└── ` edge preceded by one four-character segment per ancestor that has a later sibling; attached details prepend the same ancestor segments plus exactly one own continuation segment (`│ ` when the node has a later sibling, four spaces otherwise). Detail lines never carry structural edge markers and never add structural depth (DES-012).
- @param root {ConfigNode} Display root (virtual root or requested subtree root).
- @return {str} Complete multi-line rendering without trailing newline.

### fn `def _emit_node(` `priv` (L152-156)

### fn `def _selection_rows(param: config.ParamSpec, current: str) -> list[list[str]]` `priv` (L187-199)
- @brief Emit one real node, its details, then its child nodes.
- @brief Build `Sel | Value` rows with exactly one active marker.
- @details Recursive worker of `render_tree`; `ancestor_has_next` holds
one entry per actual ancestor recording whether that
ancestor has a later sibling (REQ-019 connector grammar).
- @param node {ConfigNode} Real configuration node to emit.
- @param ancestor_has_next {list[bool]} Later-sibling flags of ancestors.
- @param is_last {bool} True when `node` is the final sibling at depth.
- @param lines {list[str]} Output accumulator, mutated in place.
- @param param {config.ParamSpec} Selection parameter descriptor.
- @param current {str} Active value token.
- @return {None}
- @return {list[list[str]]} One `[*]` row and `[ ]` rows in enum order.

### fn `def _color_meaning(token: str) -> str` `priv` (L200-209)
- @brief Build the Meaning cell text for one enum color token.
- @param token {str} Selection enum token present in `COLOR_ANSI`.
- @return {str} Text naming the ANSI SGR code and human-readable color.

### fn `def _build_print_section(` `priv` (L210-212)

### fn `def _build_print_parameter(` `priv` (L237-240)
- @brief Build a `--print` node for one section with parameter children.
- @param section {config.SectionSpec} Section schema descriptor.
- @param payload {dict[str, Any]} Current configuration values.
- @return {ConfigNode} Section node carrying parameter child nodes.

### fn `def _build_info_section(section: config.SectionSpec) -> ConfigNode` `priv` (L268-298)
- @brief Build a `--print` node for one selection parameter.
- @brief Build an `--info` node for one fixed-schema section.
- @details Heading shows `Token = <JSON value>` plus `(default)` or
`(custom | default: <JSON default>)`; the attached
`Sel | Value` table lists exactly one `[*]` active row
(REQ-019).
- @details Metadata precedes real children: a complete `Full overwrite` command with a schema-valid sample object and a complete `Reset block` command (REQ-020).
- @param section {config.SectionSpec} Owning section descriptor.
- @param param {config.ParamSpec} Parameter schema descriptor.
- @param value {str} Current value token.
- @param section {config.SectionSpec} Section schema descriptor.
- @return {ConfigNode} Parameter node with table detail lines.
- @return {ConfigNode} Section node with metadata details and children.

### fn `def _build_info_parameter(` `priv` (L299-301)

### fn `def build_print_root(` (L345-347)
- @brief Build an `--info` node for one selection parameter.
- @details Heading reads `Token - [Type: constraints] description`;
attached details are the Default line with its restore
command, a complete shell-valid `Set cmd` using a real
schema-valid example value, and the `Allowed Values` table
(REQ-020).
- @param section {config.SectionSpec} Owning section descriptor.
- @param param {config.ParamSpec} Parameter schema descriptor.
- @return {ConfigNode} Parameter node with documentation details.

### fn `def build_info_root(payload: dict[str, Any], path: str | None) -> ConfigNode` (L384-411)
- @brief Build the display root for `--print`.
- @brief Build the display root for `--info`.
- @details Without a path the virtual `Application_Configuration` root
carries the schema sections as children; with a canonical
path the requested node becomes the unconnected display root
followed by its real descendants, without invented ancestors
(REQ-019).
- @details Same node set as `--print` with documentation heading and detail formatters; a requested path renders that node as the unconnected display root with its descendants (REQ-020).
- @param payload {dict[str, Any]} Current validated configuration.
- @param path {str | None} Raw canonical path or None for whole tree.
- @param payload {dict[str, Any]} Current validated configuration.
- @param path {str | None} Raw canonical path or None for whole schema.
- @return {ConfigNode} Display root node.
- @return {ConfigNode} Display root node.

### fn `def _fail(error: config.ConfigError) -> int` `priv` (L412-421)
- @brief Report a rendering-command failure on stderr.
- @param error {config.ConfigError} Failure carrying the diagnostic.
- @return {int} Always 1 (REQ-023).

### fn `def handle_print(args: list[str]) -> int` (L422-441)
- @brief Execute `--print [Path]` (REQ-019).
- @details Bootstraps storage, loads strictly, builds the display tree, and prints the rendering on stdout; failures print nothing on stdout and report one stderr diagnostic with exit 1.
- @param args {list[str]} CLI argument tokens excluding program name.
- @return {int} 0 on success; 1 on failure.

### fn `def handle_info(args: list[str]) -> int` (L442-459)
- @brief Execute `--info [Path]` (REQ-020).
- @details Shares the renderer with `--print`; renders schema documentation with defaults and complete command examples.
- @param args {list[str]} CLI argument tokens excluding program name.
- @return {int} 0 on success; 1 on failure.

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`ConfigNode`|class|pub|36-57|class ConfigNode|
|`display_width`|fn|pub|58-76|def display_width(text: str) -> int|
|`format_table`|fn|pub|77-122|def format_table(headers: list[str], rows: list[list[str]...|
|`border`|fn|pub|95-104|def border(left: str, middle: str, right: str) -> str|
|`data_row`|fn|pub|105-116|def data_row(cells: list[str]) -> str|
|`render_tree`|fn|pub|123-151|def render_tree(root: ConfigNode) -> str|
|`_emit_node`|fn|priv|152-156|def _emit_node(|
|`_selection_rows`|fn|priv|187-199|def _selection_rows(param: config.ParamSpec, current: str...|
|`_color_meaning`|fn|priv|200-209|def _color_meaning(token: str) -> str|
|`_build_print_section`|fn|priv|210-212|def _build_print_section(|
|`_build_print_parameter`|fn|priv|237-240|def _build_print_parameter(|
|`_build_info_section`|fn|priv|268-298|def _build_info_section(section: config.SectionSpec) -> C...|
|`_build_info_parameter`|fn|priv|299-301|def _build_info_parameter(|
|`build_print_root`|fn|pub|345-347|def build_print_root(|
|`build_info_root`|fn|pub|384-411|def build_info_root(payload: dict[str, Any], path: str | ...|
|`_fail`|fn|priv|412-421|def _fail(error: config.ConfigError) -> int|
|`handle_print`|fn|pub|422-441|def handle_print(args: list[str]) -> int|
|`handle_info`|fn|pub|442-459|def handle_info(args: list[str]) -> int|


---

# core.py | Python | 74L | 1 symbols | 2 imports | 11 comments
> Path: `src/githubtemplateastraluv/core.py`

## Imports
```
import sys
from githubtemplateastraluv import (
```

## Definitions

### fn `def main(argv: list[str] | None = None) -> int` (L22-75)
- @brief Execute the gated version check, then dispatch commands.
- @details Dispatch order: `--help` or no arguments -> help screen; `--ver` / `--version` -> aligned three-row version report fetching PyPI and GitHub with the gate bypassed (REQ-002, REQ-027..REQ-031); then `--upgrade`, optionally with the `--develop` / `--dev` source modifier selecting the GitHub development source (REQ-032..REQ-034); then `--uninstall`; then the additive configuration CLI commands `--get`, `--set`, `--unset`, `--print-raw`, `--print`, `--info` (PRJ-006); unknown input falls back to the help screen. Non-forced invocations execute the gated PyPI check before dispatch (REQ-007). Existing management dispatch and observable behavior are unchanged by the configuration branches (REQ-016..REQ-021).
- @param argv {list[str] | None} CLI arguments excluding the program name; None resolves to `sys.argv[1:]`.
- @return {int} Process exit code: 0 on handled dispatch, or the return code of the spawned `uv` subprocess for `--upgrade` `--uninstall`, or 1 for configuration CLI failures (REQ-023).
- @satisfies REQ-001 REQ-002 REQ-007 REQ-016 REQ-017 REQ-018 REQ-019 REQ-020 REQ-021 REQ-027 REQ-028 REQ-029 REQ-030 REQ-031 REQ-032 REQ-033 REQ-034 A-06 PRJ-006

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`main`|fn|pub|22-75|def main(argv: list[str] | None = None) -> int|


---

# management.py | Python | 165L | 10 symbols | 2 imports | 29 comments
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
- var `UPGRADE_DEVELOP_COMMAND = [` (L32)
- var `UNINSTALL_COMMAND = ["uv", "tool", "uninstall", "githubtemplateastraluv"]` (L46)
### fn `def is_linux() -> bool` (L52-63)
- @brief Flag column width keeping management help lines aligned.
- @brief Report whether the current operating system is Linux.
- @details `sys.platform` prefix check (covers `linux` and historical `linux2` values); all other platforms take the manual-command branch (A-09).
- @return {bool} True on Linux, False otherwise.
- @satisfies A-09 CTN-009

### fn `def _management_entry(flag: str, description: str) -> str` `priv` (L64-74)
- @brief Render one aligned management-command help line.
- @param flag {str} Command flag (e.g. `--upgrade`).
- @param description {str} Description text placed after the dash.
- @return {str} Line matching the REQ-001 template alignment.
- @satisfies REQ-001

### fn `def build_help_text(version: str) -> str` (L75-112)
- @brief Render the full help screen text (REQ-001 template).
- @details The literal `(x.y.z)` slot of the template receives the installed version (A-01); the `Commands:` section ends with the literal `...` line (A-02).
- @param version {str} Installed version in `x.y.z` format.
- @return {str} Help text without trailing newline; the caller prints it.
- @satisfies REQ-001 A-01 A-02

### fn `def print_help(version: str) -> int` (L113-123)
- @brief Print the full help screen to stdout.
- @param version {str} Installed version in `x.y.z` format.
- @return {int} Always 0.
- @satisfies REQ-001 PRJ-005

### fn `def cmd_upgrade(develop: bool = False) -> int` (L124-148)
- @brief Reinstall the tool via `uv tool install` on Linux.
- @details On Linux the exact argv selected by `develop` executes through subprocess and its exit code propagates: UPGRADE_COMMAND for the PyPI source (REQ-003), UPGRADE_DEVELOP_COMMAND for the GitHub development source (REQ-032). On any other OS no process spawns; a warning plus the matching manual command print instead (REQ-004, REQ-033).
- @param develop {bool} True selects the GitHub development source (`--upgrade --develop` / `--upgrade --dev`); False selects the PyPI source (default).
- @return {int} 0 on manual fallback or successful subprocess; otherwise the `uv` process exit code.
- @satisfies REQ-003 REQ-004 REQ-032 REQ-033 CTN-009

### fn `def cmd_uninstall() -> int` (L149-166)
- @brief Uninstall the tool via `uv tool uninstall` on Linux.
- @details On Linux the exact UNINSTALL_COMMAND argv executes through subprocess and its exit code propagates. On any other OS no process spawns; a warning plus the manual command print instead (REQ-006).
- @return {int} 0 on manual fallback or successful subprocess; otherwise the `uv` process exit code.
- @satisfies REQ-005 REQ-006 CTN-009

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM_NAME`|var|pub|12||
|`UPGRADE_COMMAND`|var|pub|18||
|`UPGRADE_DEVELOP_COMMAND`|var|pub|32||
|`UNINSTALL_COMMAND`|var|pub|46||
|`is_linux`|fn|pub|52-63|def is_linux() -> bool|
|`_management_entry`|fn|priv|64-74|def _management_entry(flag: str, description: str) -> str|
|`build_help_text`|fn|pub|75-112|def build_help_text(version: str) -> str|
|`print_help`|fn|pub|113-123|def print_help(version: str) -> int|
|`cmd_upgrade`|fn|pub|124-148|def cmd_upgrade(develop: bool = False) -> int|
|`cmd_uninstall`|fn|pub|149-166|def cmd_uninstall() -> int|


---

# version_check.py | Python | 366L | 13 symbols | 8 imports | 46 comments
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
from githubtemplateastraluv import config
```

## Definitions

### fn `def _cache_path() -> Path` `priv` (L65-79)
- @brief Placeholder replacing the version of a failed report source
- @brief Resolve the absolute cache file path from `$HOME`.
- @details Prefers the `HOME` environment variable (CTN-008); falls back to `Path.home()` when unset. Does not create directories.
- @return {Path} Absolute cache file path.
- @satisfies DES-007 CTN-008

### fn `def _read_cache(path: Path) -> dict[str, Any] | None` `priv` (L80-96)
- @brief Load the idle-time cache JSON document.
- @details Returns None when the file is absent, unreadable, unparsable, or not a JSON object; callers treat None as cache-miss.
- @param path {Path} Cache file path.
- @return {dict[str, Any] | None} Parsed cache payload or None.
- @satisfies REQ-008

### fn `def _human_timestamp(epoch_seconds: float) -> str` `priv` (L97-105)
- @brief Format an epoch value as UTC ISO-8601.
- @param epoch_seconds {float} Epoch seconds to render.
- @return {str} Timestamp shaped `YYYY-MM-DDTHH:MM:SSZ`.

### fn `def _write_cache(` `priv` (L106-109)

### fn `def _gate_allows_request(` `priv` (L134-136)
- @brief Persist the four-field idle-time cache document.
- @details Creates missing parent directories. Field names follow A-03.
- @param path {Path} Cache file path.
- @param check_epoch {float} Epoch seconds of the check attempt.
- @param idle_delay_seconds {int} Idle-delay applied after this check.
- @return {None}
- @satisfies REQ-010 REQ-011 DES-007
- @post Cache file holds exactly four fields: last_check_epoch,
last_check_human, idle_time_epoch, idle_time_human.

### fn `def _parse_version(version: str) -> tuple[int, ...]` `priv` (L155-166)
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

### fn `def _fetch_latest_pypi_version() -> str` `priv` (L167-190)
- @brief GET the PyPI JSON payload and extract the latest version.
- @details Sends a plain GET to the PyPI JSON API; no Accept header is required. Payload shape: `{"info": {"version": "x.y.z"}}`.
- @return {str} Latest published version in `x.y.z` format.
- @throws {urllib.error.URLError} On HTTP and network failures; includes HTTPError carrying the status code (e.g. 429, 503).
- @throws {TimeoutError} On the 2-second timeout expiry.
- @throws {ValueError} On unparsable payload or missing version.
- @satisfies REQ-009 REQ-028 CTN-006

### fn `def _fetch_latest_github_version() -> str` `priv` (L191-218)
- @brief GET the latest GitHub release payload and extract its version.
- @details Strips one leading `v`/`V` prefix from `tag_name`; the returned value is exactly the version downloaded by `--upgrade --develop` (REQ-032) regardless of the branch the release was tagged on.
- @return {str} Latest release version in `x.y.z` format.
- @throws {urllib.error.URLError} On HTTP and network failures; includes HTTPError carrying the status code (e.g. 429, 503).
- @throws {TimeoutError} On the 2-second timeout expiry.
- @throws {ValueError} On unparsable payload or missing tag_name.
- @satisfies REQ-029 CTN-006

### fn `def _format_report_row(label: str, value: str) -> str` `priv` (L219-229)
- @brief Render one report row with the label padded to 17 columns.
- @param label {str} Row label (e.g. `Latest @ PyPI`).
- @param value {str} Version string or `unavailable` placeholder.
- @return {str} Row shaped `<label padded to 17> : <value>` (REQ-027).
- @satisfies REQ-027

### fn `def _print_colored(color: str, message: str) -> None` `priv` (L230-240)
- @brief Print a message wrapped in an ANSI color prefix and reset.
- @param color {str} ANSI SGR prefix (bright green or bright red).
- @param message {str} Plain-text message content.
- @return {None}
- @satisfies DES-008

### fn `def _report_failure(` `priv` (L241-244)

### fn `def run_version_check(installed_version: str, force: bool = False) -> None` (L259-302)
- @brief Emit the failure note and write the 86400 s cache.
- @brief Execute the gated (or forced) online version check on PyPI.
- @details The note renders with the configured error color (REQ-026).
- @details Flow: cache read -> gate evaluation (skipped when `force`) -> PyPI JSON fetch -> version compare -> notify -> cache write. Notification colors come from the configuration subsystem with schema-default fallback (REQ-026). Success always refreshes the cache with the 3600 s idle-delay (REQ-013, A-04); fetch or parse failures print the configured error note and back off 86400 s (REQ-014, REQ-015, A-05). The call always returns normally; callers continue parsing (A-06).
- @param check_epoch {float} Epoch seconds of the failed attempt.
- @param error {BaseException} Encountered error rendered in the note.
- @param color {str} ANSI SGR prefix for the failure note.
- @param installed_version {str} Installed version in `x.y.z` format.
- @param force {bool} True bypasses the idle-time gate (REQ-002, REQ-007).
- @return {None}
- @return {None}
- @satisfies REQ-014 REQ-015 REQ-026 A-05
- @satisfies REQ-007 REQ-008 REQ-009 REQ-010 REQ-011 REQ-012 REQ-013 REQ-014 REQ-015 REQ-024 REQ-025 REQ-026

### fn `def run_version_report(installed_version: str) -> None` (L303-367)
- @brief Execute the forced dual-source version report (`--ver`).
- @details Flow: fetch PyPI -> fetch GitHub -> emit the three aligned rows. Each failed fetch emits one bright red note naming the failed source with the configured error color (REQ-030) and its row prints `unavailable` in place of the version. Rows print in order: installed, PyPI, GitHub; version columns aligned via a 17-character label pad (REQ-027). The GitHub row shows the latest release tag stripped of its `v` prefix, exactly the version downloaded by `--upgrade --develop` (REQ-029). The idle-time gate and cache file are bypassed (REQ-002); the cache write follows the PyPI outcome only: 3600 s on success, 86400 s on failure (REQ-031). The call always returns normally (A-06).
- @param installed_version {str} Installed version in `x.y.z` format.
- @return {None}
- @satisfies REQ-002 REQ-027 REQ-028 REQ-029 REQ-030 REQ-031 REQ-026

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`_cache_path`|fn|priv|65-79|def _cache_path() -> Path|
|`_read_cache`|fn|priv|80-96|def _read_cache(path: Path) -> dict[str, Any] | None|
|`_human_timestamp`|fn|priv|97-105|def _human_timestamp(epoch_seconds: float) -> str|
|`_write_cache`|fn|priv|106-109|def _write_cache(|
|`_gate_allows_request`|fn|priv|134-136|def _gate_allows_request(|
|`_parse_version`|fn|priv|155-166|def _parse_version(version: str) -> tuple[int, ...]|
|`_fetch_latest_pypi_version`|fn|priv|167-190|def _fetch_latest_pypi_version() -> str|
|`_fetch_latest_github_version`|fn|priv|191-218|def _fetch_latest_github_version() -> str|
|`_format_report_row`|fn|priv|219-229|def _format_report_row(label: str, value: str) -> str|
|`_print_colored`|fn|priv|230-240|def _print_colored(color: str, message: str) -> None|
|`_report_failure`|fn|priv|241-244|def _report_failure(|
|`run_version_check`|fn|pub|259-302|def run_version_check(installed_version: str, force: bool...|
|`run_version_report`|fn|pub|303-367|def run_version_report(installed_version: str) -> None|


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


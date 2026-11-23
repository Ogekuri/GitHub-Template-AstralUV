#!/usr/bin/env python3
## @file config_render.py
# @brief Deterministic tree renderer and table formatter for the
#        configuration CLI `--print` and `--info` commands.
# @details One shared data-driven renderer (DES-012) emits UTF-8
#          box-drawing trees from typed `ConfigNode` values for both
#          display commands; only heading and detail formatters differ.
#          Structural edges (`|-- `, `` -- `` box glyphs) mark real
#          configuration nodes only; metadata and tables are attached
#          detail lines carrying the owning node continuation prefix
#          (DES-013). Tree topology never depends on text width.
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from githubtemplateastraluv import colors, config

## @brief Ancestor continuation segment: vertical bar plus three spaces.
_PREFIX_CONTINUE = "│   "
## @brief Ancestor indent segment: exactly four ASCII spaces.
_PREFIX_INDENT = "    "
## @brief Tree edge marker for a node with a later real sibling.
_EDGE_BRANCH = "├── "
## @brief Tree edge marker for the final real sibling at a depth.
_EDGE_LAST = "└── "

## @brief Display heading of the virtual whole-tree root (never a CLI path).
_ROOT_HEADING_PRINT = "Application_Configuration - Current configuration"
## @brief Display heading of the virtual root in `--info` mode.
_ROOT_HEADING_INFO = "Application_Configuration - Configuration schema and command reference"


@dataclass
class ConfigNode:
    """@brief Typed tree node of one real configuration element.

    @details `kind` distinguishes section/dictionary branches from
             parameters; `children` holds only real configuration nodes
             while metadata and tables live in `details` as logical text
             lines (never rendered with structural edge markers).
    """
    ## @brief Canonical schema/CLI token, byte-exact (REQ-022).
    token: str
    ## @brief Full canonical path; None for the virtual display root.
    canonical_path: str | None
    ## @brief Node kind: `virtual-root`, `section`, or `parameter`.
    kind: str
    ## @brief Fully formatted heading line (no tree prefix).
    heading: str
    ## @brief Attached detail logical lines, in display order.
    details: list[str] = field(default_factory=list)
    ## @brief Ordered real child nodes.
    children: list["ConfigNode"] = field(default_factory=list)


def display_width(text: str) -> int:
    """@brief Measure the terminal display width of a string.

    @details Combining characters count zero; East Asian wide and
             fullwidth characters count two; all others count one.
    @param text {str} Text to measure.
    @return {int} Display width in terminal cells.
    """
    width = 0
    for character in text:
        if unicodedata.combining(character):
            continue
        if unicodedata.east_asian_width(character) in ("F", "W"):
            width += 2
        else:
            width += 1
    return width


def format_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """@brief Render a rectangular box-drawing table (DES-013).

    @details Column widths derive from the maximum display width of the
             header and all cells plus one space of padding on each side;
             every border and row shares identical column boundaries, so
             `┬`, `┼`, and `┴` align vertically with the `│` separators.
             Glyph contract (DES-053..DES-056): rounded outer corners
             `╭`/`╮`/`╰`/`╯`; single-line borders built from `─` with
             `┬`/`┴` top/bottom junctions and `├`/`┼`/`┤` row-separator
             junctions; double-line header separator `╞═..╪..═╡` between
             the header row and the content rows.
    @param headers {list[str]} Column header cells.
    @param rows {list[list[str]]} Data rows, each with len(headers) cells.
    @return {list[str]} Physical table lines (borders and rows).
    @satisfies DES-013, DES-053, DES-054, DES-055, DES-056
    """
    widths = [
        max(display_width(headers[column]), *(display_width(row[column]) for row in rows))
        if rows
        else display_width(headers[column])
        for column in range(len(headers))
    ]

    def border(left: str, horizontal: str, middle: str, right: str) -> str:
        """@brief Render one horizontal border line.

        @param left {str} Left corner glyph.
        @param horizontal {str} Horizontal fill glyph: `─` for single
               lines, `═` for the double header separator.
        @param middle {str} Column junction glyph.
        @param right {str} Right corner glyph.
        @return {str} Complete border line.
        """
        segments = (horizontal * (width + 2) for width in widths)
        return left + middle.join(segments) + right

    def data_row(cells: list[str]) -> str:
        """@brief Render one padded data row line.

        @param cells {list[str]} Row cells; display-padded to column width.
        @return {str} Complete row line sharing the border boundaries.
        """
        padded = " │ ".join(
            cell + " " * (widths[column] - display_width(cell))
            for column, cell in enumerate(cells)
        )
        return f"│ {padded} │"

    lines = [
        border("╭", "─", "┬", "╮"),
        data_row(headers),
        border("╞", "═", "╪", "╡"),
    ]
    for index, row in enumerate(rows):
        if index:
            lines.append(border("├", "─", "┼", "┤"))
        lines.append(data_row(row))
    lines.append(border("╰", "─", "┴", "╯"))
    return lines


def render_tree(root: ConfigNode) -> str:
    """@brief Render a node hierarchy with the canonical prefix algorithm.

    @details Implements the normative traversal: the display root prints
             without a marker and its attached details use a four-space
             indent; every real child receives exactly one `├── `/`└── `
             edge preceded by one four-character segment per ancestor
             that has a later sibling; attached details prepend the same
             ancestor segments plus exactly one own continuation segment
             (`│   ` when the node has a later sibling, four spaces
             otherwise). Detail lines never carry structural edge markers
             and never add structural depth (DES-012).
    @param root {ConfigNode} Display root (virtual root or requested
            subtree root).
    @return {str} Complete multi-line rendering without trailing newline.
    """
    lines: list[str] = [root.heading]
    for detail in root.details:
        lines.append(_PREFIX_INDENT + detail)
    for index, child in enumerate(root.children):
        _emit_node(
            child,
            ancestor_has_next=[],
            is_last=index == len(root.children) - 1,
            lines=lines,
        )
    return "\n".join(lines)


def _emit_node(
    node: ConfigNode,
    ancestor_has_next: list[bool],
    is_last: bool,
    lines: list[str],
) -> None:
    """@brief Emit one real node, its details, then its child nodes.

    @details Recursive worker of `render_tree`; `ancestor_has_next` holds
             one entry per actual ancestor recording whether that
             ancestor has a later sibling (REQ-019 connector grammar).
    @param node {ConfigNode} Real configuration node to emit.
    @param ancestor_has_next {list[bool]} Later-sibling flags of ancestors.
    @param is_last {bool} True when `node` is the final sibling at depth.
    @param lines {list[str]} Output accumulator, mutated in place.
    @return {None}
    """
    prefix = "".join(
        _PREFIX_CONTINUE if has_next else _PREFIX_INDENT
        for has_next in ancestor_has_next
    )
    edge = _EDGE_LAST if is_last else _EDGE_BRANCH
    lines.append(prefix + edge + node.heading)
    detail_prefix = prefix + (_PREFIX_INDENT if is_last else _PREFIX_CONTINUE)
    for detail in node.details:
        lines.append(detail_prefix + detail)
    for index, child in enumerate(node.children):
        _emit_node(
            child,
            ancestor_has_next=ancestor_has_next + [not is_last],
            is_last=index == len(node.children) - 1,
            lines=lines,
        )


def _selection_rows(param: config.ParamSpec, current: str) -> list[list[str]]:
    """@brief Build `Sel | Value` rows with exactly one active marker.

    @param param {config.ParamSpec} Selection parameter descriptor.
    @param current {str} Active value token.
    @return {list[list[str]]} One `[*]` row and `[ ]` rows in enum order.
    """
    return [
        ["[*]" if token == current else "[ ]", json.dumps(token)]
        for token in param.enum
    ]


def _color_meaning(token: str) -> str:
    """@brief Build the Meaning cell text for one enum token.

    @details Tokens present in `colors.PALETTE` (REQ-040) render the ANSI
             SGR code and color name; non-palette tokens degrade to a
             neutral `-` cell so the Allowed Values table stays
             schema-generic for every Selection parameter (DES-010).
    @param token {str} Selection enum token of the documented parameter.
    @return {str} `ANSI SGR <code> (<color name>)` for palette tokens;
            `-` otherwise.
    @satisfies DES-010 REQ-042
    """
    palette_entry = colors.PALETTE.get(token)
    if palette_entry is None:
        return "-"
    sgr = palette_entry[2:-1]
    return f"ANSI SGR {sgr} ({token.replace('_', ' ')})"


def _build_print_section(
    section: config.SectionSpec,
    payload: dict[str, Any],
) -> ConfigNode:
    """@brief Build a `--print` node for one section with parameter children.

    @param section {config.SectionSpec} Section schema descriptor.
    @param payload {dict[str, Any]} Current configuration values.
    @return {ConfigNode} Section node carrying parameter child nodes.
    """
    branch = payload[section.token]
    children = [
        _build_print_parameter(section, param, branch[param.token])
        for param in section.params
    ]
    return ConfigNode(
        token=section.token,
        canonical_path=section.token,
        kind="section",
        heading=(
            f"{section.token} - [Path: {section.token}] "
            f"{section.description}"
        ),
        children=children,
    )


def _build_print_parameter(
    section: config.SectionSpec,
    param: config.ParamSpec,
    value: str,
) -> ConfigNode:
    """@brief Build a `--print` node for one selection parameter.

    @details Heading shows `Token = <JSON value>` plus `(default)` or
             `(custom | default: <JSON default>)`; the attached
             `Sel | Value` table lists exactly one `[*]` active row
             (REQ-019).
    @param section {config.SectionSpec} Owning section descriptor.
    @param param {config.ParamSpec} Parameter schema descriptor.
    @param value {str} Current value token.
    @return {ConfigNode} Parameter node with table detail lines.
    """
    canonical_path = f"{section.token}:{param.token}"
    if value == param.default:
        status = "(default)"
    else:
        status = f"(custom | default: {json.dumps(param.default)})"
    heading = f"{param.token} = {json.dumps(value)} {status}"
    return ConfigNode(
        token=param.token,
        canonical_path=canonical_path,
        kind="parameter",
        heading=heading,
        details=format_table(["Sel", "Value"], _selection_rows(param, value)),
    )


def _build_info_section(section: config.SectionSpec) -> ConfigNode:
    """@brief Build an `--info` node for one fixed-schema section.

    @details Metadata precedes real children: a complete `Full overwrite`
             command with a schema-valid sample object and a complete
             `Reset block` command (REQ-020).
    @param section {config.SectionSpec} Section schema descriptor.
    @return {ConfigNode} Section node with metadata details and children.
    """
    defaults = config.default_config()[section.token]
    overwrite_sample = json.dumps(defaults, separators=(",", ":"))
    details = [
        f"Full overwrite : --set {section.token} '{overwrite_sample}'",
        f"Reset block : --unset {section.token}",
    ]
    children = [
        _build_info_parameter(section, param) for param in section.params
    ]
    return ConfigNode(
        token=section.token,
        canonical_path=section.token,
        kind="section",
        heading=(
            f"{section.token} - [Path: {section.token}] "
            f"{section.description}"
        ),
        details=details,
        children=children,
    )


def _build_info_parameter(
    section: config.SectionSpec,
    param: config.ParamSpec,
) -> ConfigNode:
    """@brief Build an `--info` node for one selection parameter.

    @details Heading reads `Token - [Type: constraints] description`;
             attached details are the Default line with its restore
             command, a complete shell-valid `Set cmd` using a real
             schema-valid example value, and the `Allowed Values` table
             (REQ-020).
    @param section {config.SectionSpec} Owning section descriptor.
    @param param {config.ParamSpec} Parameter schema descriptor.
    @return {ConfigNode} Parameter node with documentation details.
    """
    canonical_path = f"{section.token}:{param.token}"
    heading = (
        f"{param.token} - [{param.type_label}: {param.constraints}] "
        f"{param.description}"
    )
    allowed_rows = [
        [
            token,
            "default" if token == param.default else "",
            _color_meaning(token),
        ]
        for token in param.enum
    ]
    details = [
        f"Default : {json.dumps(param.default)} (restored via: "
        f"--unset {canonical_path})",
        f"Set cmd : --set {canonical_path} {param.default}",
        "Allowed Values:",
    ]
    details.extend(
        format_table(["Value", "Default", "Meaning"], allowed_rows)
    )
    return ConfigNode(
        token=param.token,
        canonical_path=canonical_path,
        kind="parameter",
        heading=heading,
        details=details,
    )


def build_print_root(
    payload: dict[str, Any],
    path: str | None,
) -> ConfigNode:
    """@brief Build the display root for `--print`.

    @details Without a path the virtual `Application_Configuration` root
             carries the schema sections as children; with a canonical
             path the requested node becomes the unconnected display root
             followed by its real descendants, without invented ancestors
             (REQ-019).
    @param payload {dict[str, Any]} Current validated configuration.
    @param path {str | None} Raw canonical path or None for whole tree.
    @return {ConfigNode} Display root node.
    @satisfies DES-058
    """
    if path is None:
        return ConfigNode(
            token="Application_Configuration",
            canonical_path=None,
            kind="virtual-root",
            heading=_ROOT_HEADING_PRINT,
            children=[
                _build_print_section(section, payload) for section in config.SCHEMA
            ],
        )
    segments = config.resolve_segments(path)
    section = config.section(segments[0])
    if section is None:
        raise config.ConfigError(
            f"unknown configuration section {segments[0]!r}"
        )
    if len(segments) == 1:
        return _build_print_section(section, payload)
    param = section.param(segments[1])
    if param is None:
        raise config.ConfigError(f"unknown parameter in path {path!r}")
    return _build_print_parameter(
        section, param, payload[section.token][param.token]
    )


def build_info_root(payload: dict[str, Any], path: str | None) -> ConfigNode:
    """@brief Build the display root for `--info`.

    @details Same node set as `--print` with documentation heading and
             detail formatters; a requested path renders that node as the
             unconnected display root with its descendants (REQ-020).
    @param payload {dict[str, Any]} Current validated configuration.
    @param path {str | None} Raw canonical path or None for whole schema.
    @return {ConfigNode} Display root node.
    @satisfies DES-058
    """
    if path is None:
        return ConfigNode(
            token="Application_Configuration",
            canonical_path=None,
            kind="virtual-root",
            heading=_ROOT_HEADING_INFO,
            children=[_build_info_section(section) for section in config.SCHEMA],
        )
    segments = config.resolve_segments(path)
    section = config.section(segments[0])
    if section is None:
        raise config.ConfigError(
            f"unknown configuration section {segments[0]!r}"
        )
    if len(segments) == 1:
        return _build_info_section(section)
    param = section.param(segments[1])
    if param is None:
        raise config.ConfigError(f"unknown parameter in path {path!r}")
    return _build_info_parameter(section, param)


def _fail(error: config.ConfigError) -> int:
    """@brief Report a rendering-command failure on stderr.

    @param error {config.ConfigError} Failure carrying the diagnostic.
    @return {int} Always 1 (REQ-023).
    """
    print(f"Error: {error}", file=sys.stderr)
    return 1


def handle_print(args: list[str]) -> int:
    """@brief Execute `--print [Path]` (REQ-019).

    @details Bootstraps storage, loads the schema-shaped display view via
             `config.load_display` so content persisted by an older
             schema version never blocks rendering (DES-010, TST-008),
             builds the display tree, and prints the rendering on stdout;
             genuine failures (absent, unreadable, malformed JSON, or
             non-object file; invalid operands or paths) print nothing
             on stdout and report one stderr diagnostic with exit 1
             (REQ-023).
    @param args {list[str]} CLI argument tokens excluding program name.
    @return {int} 0 on success; 1 on failure.
    """
    try:
        operands = config.operand_values(args, "--print", 0, 1)
        config.ensure_bootstrapped()
        payload = config.load_display()
        root = build_print_root(payload, operands[0] if operands else None)
    except config.ConfigError as error:
        return _fail(error)
    print(render_tree(root))
    return 0


def handle_info(args: list[str]) -> int:
    """@brief Execute `--info [Path]` (REQ-020).

    @details Shares the renderer with `--print` and loads the same
             schema-shaped display view via `config.load_display` so
             content persisted by an older schema version never blocks
             rendering (DES-010, TST-008); renders schema documentation
             with defaults and complete command examples; genuine
             failures print nothing on stdout and report one stderr
             diagnostic with exit 1 (REQ-023).
    @param args {list[str]} CLI argument tokens excluding program name.
    @return {int} 0 on success; 1 on failure.
    """
    try:
        operands = config.operand_values(args, "--info", 0, 1)
        config.ensure_bootstrapped()
        payload = config.load_display()
        root = build_info_root(payload, operands[0] if operands else None)
    except config.ConfigError as error:
        return _fail(error)
    print(render_tree(root))
    return 0

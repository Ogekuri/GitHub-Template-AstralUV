## @file __init__.py
# @brief Expose package-level metadata and public CLI entrypoint symbols.
# @details Defines stable module exports for downstream imports and
#          runtime version checks, mirroring the skeleton schema.

## @brief Store semantic version string for package metadata.
# @details Used by CLI usage/version output and by release automation
#          checks; single source of truth consumed by core.main dispatch
#          and mirrored in pyproject.toml, scripts/templateastraluv.sh,
#          README.md, and uv.lock.
__version__ = "0.0.8"

from githubtemplateastraluv.core import main  # noqa: F401

## @brief Enumerate public symbols exported by package root.
# @details Constrains wildcard-import surface to the version constant and
#          the CLI main callable.
__all__ = ["__version__", "main"]

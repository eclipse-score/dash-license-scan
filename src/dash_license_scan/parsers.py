"""Parsers for supported lockfile formats used by the CLI wrapper."""

import logging
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

try:  # Python >=3.11
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # Python 3.10 fallback
    import tomli as tomllib  # type: ignore[assignment]  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)


def parse(file: Path) -> list[str]:
    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"
    if not file.exists():
        sys.exit(f"lockfile not found: {file}")

    # TODO: sync typical filenames with e.g. dependabot definitions
    if file.stem == "requirements" and file.suffix in (".txt", ".out"):
        return parse_pypi(file)
    elif file.name == "Cargo.lock":
        return parse_crate(file)
    elif file.name == "uv.lock":
        return parse_uv_lock(file)
    else:
        sys.exit(f"Unsupported lockfile type: {file}")


def read_file_lines(file: Path) -> Generator[str, None, None]:
    """Yield non-empty, non-comment lines from a text file."""
    text = file.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def parse_pypi(file: Path):
    """Parse a pip requirements file into dash-licenses dependency coordinates."""
    deps: list[str] = []

    for line in read_file_lines(file):
        # Skip --hash lines (they're options for the previous requirement)
        if line.startswith("--hash="):
            continue

        if "==" in line:
            name, _, version = line.strip("\\ ").partition("==")
            deps.append(f"pypi/pypi/-/{name}/{version}")
        else:
            logger.warning(f"Skipping unsupported pip requirement line: {line}")

    return deps


def parse_crate(file: Path):
    """Parse a Cargo.lock and extract crates.io dependencies."""
    deps: list[str] = []

    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"

    try:
        data = cast(
            "dict[str, object]", tomllib.loads(file.read_text(encoding="utf-8"))
        )
    except Exception as exc:  # pragma: no cover - defensive error surface
        raise ValueError(f"Failed to parse Cargo.lock as TOML: {file}") from exc

    packages = data.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("Invalid Cargo.lock: 'package' section missing or malformed")

    for pkg in packages:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(pkg, dict):
            continue
        pkg = cast("dict[str, object]", pkg)

        name = pkg.get("name")
        version = pkg.get("version")
        source = pkg.get("source", "") or ""

        if not (name and version):
            continue

        # Only crates.io is supported today; detect via presence of 'crates' in source.
        if source and "crates" not in str(source).lower():
            raise ValueError(f"Unknown crate registry source: {source}")

        deps.append(f"crate/cratesio/-/{name}/{version}")

    return deps


def parse_uv_lock(file: Path):
    """Parse Python project dependencies from uv.lock.

    Extracts pinned package versions from the uv lockfile format.
    Only includes packages from PyPI registry.
    """
    deps: list[str] = []

    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"

    try:
        data = cast("dict[str, Any]", tomllib.loads(file.read_text(encoding="utf-8")))
    except Exception as exc:  # pragma: no cover - defensive error surface
        raise ValueError(f"Failed to parse {file.name} as TOML: {file}") from exc

    packages = data.get("package", [])
    if not isinstance(packages, list):
        logger.warning("Invalid uv.lock: 'package' section missing or malformed")
        return deps

    for pkg in packages:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(pkg, dict):
            continue
        pkg = cast("dict[str, Any]", pkg)

        name = pkg.get("name")
        version = pkg.get("version")
        source = pkg.get("source", {})

        if not (name and version):
            continue

        # Only include packages from PyPI registry (default source)
        if isinstance(source, dict):
            source = cast("dict[str, Any]", source)
            registry = source.get("registry", "https://pypi.org/simple")
            # Only include PyPI packages; skip other registries
            if registry and "pypi.org" not in registry:
                logger.debug(
                    f"Skipping package from non-PyPI registry: {name} from {registry}"
                )
                continue

        deps.append(f"pypi/pypi/-/{name}/{version}")

    return deps

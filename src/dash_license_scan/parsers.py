import logging
import sys
from collections.abc import Sequence
from pathlib import Path

logger = logging.getLogger(__name__)


def parse(file: Path) -> list[str]:
    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"
    if not file.exists():
        sys.exit(f"lockfile not found: {file}")

    if file.suffix in {".txt", ".pip", ".requirements"}:
        return parse_pypi(file)
    elif file.name == "Cargo.lock" or file.suffix == ".lock":
        return parse_crate(file)
    else:
        sys.exit(f"Unsupported lockfile type: {file}")


def lines(text: str) -> Sequence[str]:
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        yield line


def parse_pypi(file: Path):
    deps: list[str] = []

    for line in lines(file.read_text(encoding="utf-8")):
        if "==" in line:
            name, _, version = line.strip("\\ ").partition("==")
            deps.append(f"pypi/pypi/-/{name}/{version}")
        else:
            logger.warning(f"Skipping unsupported pip requirement line: {line}")

    return deps


def parse_crate(file: Path):
    deps: list[str] = []

    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"

    text = file.read_text(encoding="utf-8")

    # Split into [[package]] blocks and parse simple key=value lines into a dict.
    for block in text.split("[[package]]"):
        block = block.strip()
        if not block:
            continue

        fields: dict[str, str] = {}
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            fields[k.strip()] = v.strip().strip('"')

        name = fields.get("name")
        version = fields.get("version")
        source = fields.get("source")

        if not (name and version):
            continue

        # Only crates.io is supported today; detect via presence of 'crates' in source.
        if source and "crates" not in source.lower():
            raise ValueError(f"Unknown crate registry source: {source}")

        deps.append(f"crate/cratesio/-/{name}/{version}")

    return deps

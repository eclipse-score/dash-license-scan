import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from dash_license_scan import __version__, jar

log = getLogger(__name__)


@dataclass
class Params:
    dry_run: bool
    lockfiles: list[Path]
    verbose: bool
    summary: Path | None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=f"Wrapper around eclipse-dash/dash-licenses.\nUses bundled {jar.get_jar().name}.",
    )
    _ = p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    _ = p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print detected dependencies without executing dash-licenses",
    )
    _ = p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    _ = p.add_argument(
        "--summary",
        type=Path,
        help="Optional path to write the dash-licenses summary output. If omitted results are printed to stdout.",
    )
    _ = p.add_argument(
        "lockfiles",
        nargs="+",
        help="One or more lockfiles to scan (e.g., requirements.txt, Cargo.lock)",
        type=Path,
    )

    return p


def parse_args(argv: Sequence[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)

    return Params(
        dry_run=args.dry_run,  # pyright: ignore[reportAny]
        lockfiles=args.lockfiles,  # pyright: ignore[reportAny]
        verbose=args.verbose,  # pyright: ignore[reportAny]
        summary=args.summary,  # pyright: ignore[reportAny]
    )

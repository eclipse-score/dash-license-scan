import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path

from dash_license_scan import __version__, jar

log = getLogger(__name__)


class OutputFormat(str, Enum):
    MD = "md"


@dataclass
class Params:
    dry_run: bool
    lockfiles: list[Path]
    verbose: bool
    trigger_review: bool
    format: OutputFormat
    comply_with: str | None = None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=f"Wrapper around eclipse-dash/dash-licenses.\nUses bundled {jar.bundled_jar().name}.",
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
        "--trigger-review",
        action="store_true",
        help="Trigger license review process (in case of unknown licenses)",
    )
    _ = p.add_argument(
        "--format",
        choices=list(OutputFormat),
        default=OutputFormat.MD,
        help="Format of the summary output",
    )
    _ = p.add_argument(
        "--comply-with",
        metavar="LICENSE",
        help="Check compliance with specified license (currently only 'Apache-2.0' is supported)",
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

    p = Params(
        dry_run=args.dry_run,
        lockfiles=args.lockfiles,
        verbose=args.verbose,
        trigger_review=args.trigger_review,
        format=OutputFormat(args.format),
        comply_with=args.comply_with,
    )

    if p.comply_with and p.comply_with != "Apache-2.0":
        parser.error(
            f"--comply-with: only 'Apache-2.0' is currently supported, got '{p.comply_with}'"
        )

    if p.dry_run and p.trigger_review:
        parser.error("--dry-run and --trigger-review cannot be used together")

    return p

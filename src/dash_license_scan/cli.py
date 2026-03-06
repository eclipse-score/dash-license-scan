import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path

from dotenv import load_dotenv

from dash_license_scan import __version__, jar

log = getLogger(__name__)


class OutputFormat(str, Enum):
    MD = "md"
    JSON = "json"


@dataclass
class Params:
    dry_run: bool
    lockfiles: list[Path]
    verbose: bool
    trigger_review: bool
    format: OutputFormat
    comply_with: list[str]
    token: str | None
    project: str | None


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
        action="append",
        choices=["ASF", "EF"],
        metavar="POLICY",
        help="Check compliance with specified policy/policies (ASF, EF)",
    )

    _ = p.add_argument(
        "lockfiles",
        nargs="*",
        help=(
            "One or more lockfiles to scan (e.g., requirements.txt, Cargo.lock).\n"
            "If not provided, the tool will attempt to auto-detect lockfiles in the current directory."
        ),
        type=Path,
    )

    return p


def parse_args_and_env(argv: Sequence[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)

    _ = load_dotenv()
    token = os.getenv("DASH_TOKEN") or os.getenv("ECLIPSE_GITLAB_API_TOKEN")
    project = os.getenv("ECLIPSE_PROJECT")

    p = Params(
        dry_run=args.dry_run,
        lockfiles=args.lockfiles,
        verbose=args.verbose,
        trigger_review=args.trigger_review,
        format=OutputFormat(args.format),
        comply_with=sorted(set(args.comply_with or [])),
        token=token,
        project=project,
    )

    if p.dry_run and p.trigger_review:
        parser.error("--dry-run and --trigger-review cannot be used together")

    if args.trigger_review and (not project or not token):
        parser.error(
            """
To trigger review mode, please ensure the following environment variables are set:
    - DASH_TOKEN or ECLIPSE_GITLAB_API_TOKEN
    - ECLIPSE_PROJECT

Refer to the documentation for more details on setting these variables.
            """
        )

    return p

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from dash_license_scan import jar
from dash_license_scan.cli import parse_args
from dash_license_scan.parsers import parse

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------------------------------------


def parse_all_lockfiles(lockfiles: list[Path]) -> list[str]:
    deps: list[str] = []

    for file in lockfiles:
        log.debug(f"Parsing lockfile: {file}")
        parsed = parse(file)
        log.debug(f"Parsed dependencies from {file}: {parsed}")

        deps.extend(parsed)

    return deps


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.verbose:
        log.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate Java availability up-front (even for dry-run) so users get immediate
    # feedback if their environment is missing the JRE required by dash-licenses.
    jar.require_java()

    _ = load_dotenv()
    token = os.getenv("DASH_TOKEN") or os.getenv("ECLIPSE_GITLAB_API_TOKEN")
    project = os.getenv("ECLIPSE_PROJECT")

    log.debug("Starting dash_license_scan.main(%s)", argv)
    log.debug("Parsed args: %s", args)
    log.debug(f"project: {project}, token: {'set' if token else 'not set'}")

    if args.review and (not project or not token):
        log.error(
            """
To trigger review mode, please ensure the following environment variables are set:
    - DASH_TOKEN or ECLIPSE_GITLAB_API_TOKEN
    - ECLIPSE_PROJECT

Refer to the documentation for more details on setting these variables.
            """
        )
        raise SystemExit(1)

    deps = parse_all_lockfiles(args.lockfiles)

    if len(deps) == 0:
        log.warning("No dependencies found to scan.")
        return 2  # No dependencies found is probably an error

    log.info(f"Scanning {len(deps)} dependencies...")

    result = jar.run_jar(
        dependencies="\n".join(deps),
        verbose=args.verbose,
        dry_run=args.dry_run,
        project=project,
        token_for_review=token if args.review else None,
    )

    log.debug(f"Dash Licenses log: {result.log}")

    if args.format == "md":
        status = (
            "✅ No issues found"
            if not result.issues
            else f"❌ {len(result.issues)} Issues found"
        )

        print(f"# Dash License Scan: {status}")
        print(result.summarize)
        if args.review and result.issues:
            print("License review process was triggered.")
            for issue in result.issues:
                print(f"* {issue}")

    return 1 if result.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

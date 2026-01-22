from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from dash_license_scan import jar
from dash_license_scan.cli import parse_args
from dash_license_scan.parsers import parse

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

    print(f"Scanning {len(deps)} dependencies...")

    # TODO: should we cache the results? Forever? For some minutes? Configurable?
    issues, out = jar.run_jar(
        dependencies="\n".join(deps),
        verbose=args.verbose,
        result_file=Path(args.summary) if args.summary else None,
        dry_run=args.dry_run,
        project=project,
        token_for_review=token if args.review else None,
    )

    print("")
    print(
        f"Dash Licenses Summary Output: {'OK' if issues == 0 else f'{issues} Issues Found'}"
    )
    print(out)

    if args.review and issues > 0:
        print(
            "License review process was triggered. See https://gitlab.eclipse.org/eclipsefdn/emo-team/iplab/-/issues/?sort=created_date for details/status."
        )

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

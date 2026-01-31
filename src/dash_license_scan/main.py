from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dash_license_scan import jar
from dash_license_scan.cli import parse_args_and_env
from dash_license_scan.compliance import (
    ComplianceResult,
    evaluate_compatibility,
)
from dash_license_scan.outputs import write_markdown_report
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
    args = parse_args_and_env(argv)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        log.setLevel(logging.DEBUG)

    # Note: do not log/print args here, as they may contain sensitive info (tokens)
    log.debug("Starting dash_license_scan.main(%s)", argv)

    # Validate Java availability up-front (even for dry-run) so users get immediate
    # feedback if their environment is missing the JRE required by dash-licenses.
    jar.require_java()

    deps = parse_all_lockfiles(args.lockfiles)

    if len(deps) == 0:
        log.warning("No dependencies found to scan.")
        return 2  # No dependencies found is probably an error

    log.info(f"Scanning {len(deps)} dependencies...")

    result = jar.run_jar(
        dependencies="\n".join(deps),
        verbose=args.verbose,
        dry_run=args.dry_run,
        project=args.project,
        token=args.token,
        trigger_review=args.trigger_review,
    )

    log.debug(f"Dash Licenses log:\n{result.log}")

    log.debug("Dash Licenses summary:\n%s", result.summary)

    # Step 3: Evaluate compliance (only if --comply-with is set)
    # combined_status[package][policy] = status
    extra_policies_status: dict[str, dict[str, ComplianceResult]] = {}
    for policy in args.comply_with:
        log.info(f"Evaluating compliance with {policy}...")
        for dep in result.dependencies:
            comp = evaluate_compatibility(dep.license_raw, policy)
            if dep.package not in extra_policies_status:
                extra_policies_status[dep.package] = {}
            extra_policies_status[dep.package][policy] = comp

    if args.format == "md":
        write_markdown_report(result, extra_policies_status)
    else:
        log.error(f"Unknown output format: {args.format}")
        return 2

    return 1 if result.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

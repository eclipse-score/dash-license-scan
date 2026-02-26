from __future__ import annotations

import logging
from pathlib import Path

from dash_license_scan import jar
from dash_license_scan.cli import parse_args_and_env
from dash_license_scan.compliance import (
    evaluate_compatibility,
)
from dash_license_scan.outputs import DependencyReport, write_markdown_report
from dash_license_scan.parsers import Dependency, parse

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

LOCKFILE_NAMES = [
    "requirements.txt",
    "requirements-dev.txt",
    "uv.lock",
    "Cargo.lock",
    # CycloneDX/cdx JSON SBOMs
    "*cyclonedx*.json",
    "*cdx*.json",
    "*spdx*.json",
    # Add more variants as needed"
]
# ----------------------------------------------------------------------------------


def parse_all_lockfiles(lockfiles: list[Path]) -> dict[str, Dependency]:
    deps: dict[str, Dependency] = {}

    for file in lockfiles:
        log.debug(f"Parsing lockfile: {file}")
        parsed = parse(file)
        log.debug(f"Parsed dependencies from {file}: {parsed}")

        for coord, dep in parsed.items():
            existing = deps.get(coord)
            if existing:
                existing.dev = existing.dev and dep.dev
            else:
                deps[coord] = dep

    return deps


def find_lockfiles(root: Path) -> list[Path]:
    lockfiles = []
    for name in LOCKFILE_NAMES:
        lockfiles.extend(root.rglob(name))
    return lockfiles


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

    lockfiles: list[Path] = args.lockfiles or []
    if not lockfiles:
        # If no lockfiles are provided, automatically search for typical lockfiles in all subdirectories from the project root.
        log.info(
            "No lockfiles specified, searching for typical lockfiles in subdirectories from project root..."
        )

        root: Path = Path.cwd()
        lockfiles = find_lockfiles(root)

    log.debug(f"Lockfiles to scan: {lockfiles}")
    deps = parse_all_lockfiles(lockfiles)

    if len(deps) == 0:
        log.warning("No dependencies found to scan.")
        return 2  # No dependencies found is probably an error

    log.info(f"Scanning {len(deps)} dependencies...")

    result = jar.run_jar(
        dependencies="\n".join(deps.keys()),
        verbose=args.verbose,
        dry_run=args.dry_run,
        project=args.project,
        token=args.token,
        trigger_review=args.trigger_review,
    )

    log.debug(f"Dash Licenses log:\n{result.log}")

    log.debug("Dash Licenses summary:\n%s", result.summary)

    # 1. parse lock files
    # 2. run jar to get license info
    # 3. evaluate compliance with policies
    # 4. print report

    # parsed : dict[str, Dependency] = parse_all_lockfiles(args.lockfiles)
    # jar_result: dict[..., jar.JarResult] = jar.run_jar(...)
    # compliance_results: dict[str, ComplianceResult] = {}
    # # merge 3 dicts! wtf
    # print_result()

    prod_coords: set[str] = set()
    dev_coords: set[str] = set()
    for orig_dep in deps.values():
        coord = orig_dep.to_coordinate()
        if orig_dep.dev:
            dev_coords.add(coord)
        else:
            prod_coords.add(coord)

    reports: dict[str, DependencyReport] = {}
    for jar_dep in result.dependencies:
        coord = jar_dep.package
        is_dev = coord in dev_coords and coord not in prod_coords
        report = DependencyReport(
            package=jar_dep.package,
            license_raw=jar_dep.license_raw,
            license_pretty=jar_dep.license_pretty,
            status=jar_dep.status,
            clearlydefined_or_ticket=jar_dep.clearlydefined_or_ticket,
            extra_policies={},
            is_dev=is_dev,
        )
        reports[jar_dep.package] = report

    # Step 3: Evaluate compliance (only if --comply-with is set)
    for policy in args.comply_with:
        log.info(f"Evaluating compliance with {policy}...")
        for dep in result.dependencies:
            reports[dep.package].extra_policies[policy] = evaluate_compatibility(
                dep.license_raw, policy
            )

    if args.format == "md":
        write_markdown_report(reports)
    else:
        log.error(f"Unknown output format: {args.format}")
        return 2

    return 1 if result.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

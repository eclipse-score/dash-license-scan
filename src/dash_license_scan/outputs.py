from dataclasses import dataclass

from dash_license_scan.compliance import ComplianceResult, ComplianceStatus


@dataclass
class DependencyReport:
    """Combined information for a single dependency in the report."""

    package: str
    license_raw: str
    license_pretty: str
    status: ComplianceStatus
    clearlydefined_or_ticket: str
    extra_policies: dict[str, ComplianceResult]
    is_dev: bool


def _compliance_status_to_markdown(result: ComplianceStatus) -> str:
    if result == ComplianceStatus.ALLOWED:
        return "✅"
    elif result == ComplianceStatus.RESTRICTED:
        return "❌"
    elif result == ComplianceStatus.UNCERTAIN:
        return "❓"
    else:
        return str(result)


def _compliance_result_to_markdown(comp: ComplianceResult) -> str:
    status = _compliance_status_to_markdown(comp.status)
    if problems := ", ".join(comp.problems) if comp.problems else "":
        return f"{status} ({problems})"
    else:
        return status


def _clearlydefined_or_ticket_to_link(package: str, src: str) -> str:
    if src == "clearlydefined":
        return f"[clearlydefined](https://clearlydefined.io/definitions/{package})"
    elif src.startswith("#"):
        issue_id = src[1:]
        return f"[Eclipse ipLab {issue_id}](https://gitlab.eclipse.org/eclipsefdn/emo-team/iplab/-/issues/{issue_id})"
    else:
        return src


def results_to_markdown(results: dict[str, ComplianceResult]) -> str:
    parts = []
    if len(results) == 1:
        # Single result, no need to label
        only_result = next(iter(results.values()))
        return _compliance_result_to_markdown(only_result)

    # If all results are ALLOWED with no problems, just show checkmark
    if all(
        comp.status == ComplianceStatus.ALLOWED and not comp.problems
        for comp in results.values()
    ):
        return "✅"

    for policy, comp in results.items():
        parts.append(f"**{policy}**: {_compliance_result_to_markdown(comp)}")
    return "<br/>".join(parts)


def _aggregate_status_results(
    base_status: ComplianceStatus,
    extra_policies: dict[str, ComplianceResult],
) -> dict[str, ComplianceResult]:
    results: dict[str, ComplianceResult] = {
        "Eclipse Dash": ComplianceResult(status=base_status, problems=[])
    }
    for policy, comp in extra_policies.items():
        results[policy] = comp
    return results


def _print_markdown_table(
    reports: list[DependencyReport],
    title: str,
) -> None:
    """Print a markdown table for a list of dependency reports."""
    print(f"# Dash License Scan - {title}")
    print("| Package | License | Status | Details |")
    print("|---------|---------|--------|---------|")
    for report in reports:
        results = _aggregate_status_results(report.status, report.extra_policies)
        status = results_to_markdown(results)
        link = _clearlydefined_or_ticket_to_link(
            report.package, report.clearlydefined_or_ticket
        )
        print(f"| {report.package} | {report.license_pretty} | {status} | {link} |")
    print()


def write_markdown_report(reports_by_package: dict[str, DependencyReport]) -> None:
    """Write markdown report split by production/dev dependencies.

    Args:
        reports_by_package: Mapping of package coordinate to DependencyReport.
    """
    reports = list(reports_by_package.values())
    # Separate by dev status
    prod_reports = [r for r in reports if not r.is_dev]
    dev_reports = [r for r in reports if r.is_dev]

    # Print production dependencies table
    if prod_reports:
        _print_markdown_table(prod_reports, "Production Dependencies")

    # Print development dependencies table
    if dev_reports:
        _print_markdown_table(dev_reports, "Development Dependencies")

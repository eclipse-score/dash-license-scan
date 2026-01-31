
from dash_license_scan.compliance import ComplianceResult, ComplianceStatus
from dash_license_scan.jar import JarResult


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

def _clearlydefined_or_ticket_to_link(src: str) -> str:
    if src == "clearlydefined":
        return "[clearlydefined (DRAFT)](https://clearlydefined.io/definitions/)"
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

    for policy, comp in results.items():
        parts.append(f"**{policy}**: {_compliance_result_to_markdown(comp)}")
    return "<br/>".join(parts)

def _aggregate_status_results(
    base_status: ComplianceStatus,
    extra_policies: dict[str, ComplianceResult],
) -> dict[str, ComplianceResult]:
    results: dict[str, ComplianceResult] = {"Eclipse Dash": ComplianceResult(status=base_status, problems=[])}
    for policy, comp in extra_policies.items():
        results[policy] = comp
    return results

def write_markdown_report(result: JarResult, extra_policies_tatus: dict[str, dict[str, ComplianceResult]]) -> None:

    print("# Dash License Scan")
    print("| Package | License | Status | Src |")
    print("|---------|---------|--------|-----|")
    for dep in result.dependencies:
        results = _aggregate_status_results(dep.status, extra_policies_tatus.get(dep.package, {}))
        status = results_to_markdown(results)
        link = _clearlydefined_or_ticket_to_link(dep.clearlydefined_or_ticket)
        print(f"| {dep.package} | {dep.license_pretty} | {status} | {link} |")
    print()

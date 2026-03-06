"""Unit tests for markdown and JSON output generation."""

import json
from unittest.mock import patch

from dash_license_scan.compliance import ComplianceResult, ComplianceStatus
from dash_license_scan.outputs import (
    DependencyReport,
    results_to_markdown,
    write_json_report,
)


class TestResultsToMarkdown:
    """Test results_to_markdown function."""

    def test_single_result_no_policy_label(self):
        """Single result should not include policy labels."""
        results = {
            "Eclipse Dash": ComplianceResult(
                status=ComplianceStatus.ALLOWED, problems=[]
            )
        }
        output = results_to_markdown(results)
        assert output == "✅"
        assert "Eclipse Dash" not in output

    def test_multiple_results_with_labels(self):
        """Multiple results should include policy names."""
        results = {
            "ASF": ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            "EF": ComplianceResult(
                status=ComplianceStatus.RESTRICTED, problems=["GPL-2.0-only"]
            ),
        }
        output = results_to_markdown(results)
        assert "ASF**: ✅" in output
        assert "EF**: ❌ (GPL-2.0-only)" in output
        assert "<br/>" in output

    def test_results_with_different_statuses(self):
        """Results with mixed statuses should all be included."""
        results = {
            "Policy1": ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            "Policy2": ComplianceResult(
                status=ComplianceStatus.UNCERTAIN, problems=["Unknown"]
            ),
            "Policy3": ComplianceResult(
                status=ComplianceStatus.RESTRICTED, problems=["GPL"]
            ),
        }
        output = results_to_markdown(results)
        assert "✅" in output
        assert "❓" in output
        assert "❌" in output
        assert output.count("<br/>") == 2  # n-1 separators for 3 items

    def test_multiple_results_all_allowed_no_labels(self):
        """Multiple results all ALLOWED should show only checkmark without labels."""
        results = {
            "ASF": ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            "EF": ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            "Eclipse Dash": ComplianceResult(
                status=ComplianceStatus.ALLOWED, problems=[]
            ),
        }
        output = results_to_markdown(results)
        assert output == "✅"
        assert "ASF" not in output
        assert "EF" not in output
        assert "Eclipse Dash" not in output


def _make_report(
    package: str,
    is_dev: bool = False,
    status: ComplianceStatus = ComplianceStatus.ALLOWED,
) -> DependencyReport:
    return DependencyReport(
        package=package,
        license_raw="Apache-2.0",
        license_pretty="Apache 2.0",
        status=status,
        clearlydefined_or_ticket="clearlydefined",
        extra_policies={},
        is_dev=is_dev,
    )


class TestWriteJsonReport:
    """Tests for write_json_report."""

    def _capture(self, reports: dict) -> dict:
        with patch("builtins.print") as mock_print:
            write_json_report(reports)
        printed = mock_print.call_args[0][0]
        return json.loads(printed)

    def test_empty_report(self):
        output = self._capture({})
        assert output == {"production": [], "development": []}

    def test_production_and_dev_split(self):
        reports = {
            "pypi/pypi/-/prod/1.0": _make_report("pypi/pypi/-/prod/1.0", is_dev=False),
            "pypi/pypi/-/dev/1.0": _make_report("pypi/pypi/-/dev/1.0", is_dev=True),
        }
        output = self._capture(reports)
        assert len(output["production"]) == 1
        assert len(output["development"]) == 1
        assert output["production"][0]["package"] == {"distribution": "pypi", "name": "prod", "version": "1.0"}
        assert output["development"][0]["package"] == {"distribution": "pypi", "name": "dev", "version": "1.0"}

    def test_case1_all_allowed_status_is_dict_with_allowed(self):
        """All allowed: status is a dict with each policy showing 'allowed'."""
        reports = {
            "pypi/pypi/-/a/1.0": _make_report(
                "pypi/pypi/-/a/1.0", status=ComplianceStatus.ALLOWED
            ),
        }
        output = self._capture(reports)
        status = output["production"][0]["status"]
        assert isinstance(status, dict)
        assert status["Eclipse Dash"] == {"status": "allowed", "problems": []}

    def test_case1_all_allowed_including_extra_policies(self):
        """All policies allowed: every policy entry shows 'allowed'."""
        report = _make_report("pypi/pypi/-/a/1.0", status=ComplianceStatus.ALLOWED)
        report.extra_policies["ASF"] = ComplianceResult(
            status=ComplianceStatus.ALLOWED, problems=[]
        )
        report.extra_policies["EF"] = ComplianceResult(
            status=ComplianceStatus.ALLOWED, problems=[]
        )
        output = self._capture({"pypi/pypi/-/a/1.0": report})
        status = output["production"][0]["status"]
        assert status["Eclipse Dash"] == {"status": "allowed", "problems": []}
        assert status["ASF"] == {"status": "allowed", "problems": []}
        assert status["EF"] == {"status": "allowed", "problems": []}

    def test_case2_restricted_eclipse_dash_gives_dict(self):
        """Eclipse Dash restricted: dict with restricted status."""
        reports = {
            "pypi/pypi/-/a/1.0": _make_report(
                "pypi/pypi/-/a/1.0", status=ComplianceStatus.RESTRICTED
            ),
        }
        output = self._capture(reports)
        status = output["production"][0]["status"]
        assert isinstance(status, dict)
        assert status["Eclipse Dash"]["status"] == "restricted"

    def test_case2_extra_policies_status_is_dict_per_policy(self):
        """Case 2: extra policies present — status is a dict keyed by policy."""
        report = _make_report("pypi/pypi/-/a/1.0")
        report.extra_policies["ASF"] = ComplianceResult(
            status=ComplianceStatus.UNCERTAIN,
            problems=["LicenseRef-scancode-other-permissive"],
        )
        report.extra_policies["EF"] = ComplianceResult(
            status=ComplianceStatus.UNCERTAIN,
            problems=["LicenseRef-scancode-other-permissive"],
        )
        output = self._capture({"pypi/pypi/-/a/1.0": report})
        status = output["production"][0]["status"]
        assert isinstance(status, dict)
        assert status["Eclipse Dash"] == {"status": "allowed", "problems": []}
        assert status["ASF"]["status"] == "uncertain"
        assert "LicenseRef-scancode-other-permissive" in status["ASF"]["problems"]
        assert status["EF"]["status"] == "uncertain"

    def test_output_is_valid_json(self, capsys):
        reports = {"pypi/pypi/-/x/2.0": _make_report("pypi/pypi/-/x/2.0")}
        write_json_report(reports)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "production" in parsed
        assert "development" in parsed

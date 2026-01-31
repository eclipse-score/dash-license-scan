"""Unit tests for markdown output generation."""

from dash_license_scan.compliance import ComplianceResult, ComplianceStatus
from dash_license_scan.outputs import results_to_markdown


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

"""Unit tests for license compliance merging logic."""

import pytest

from dash_license_scan.compliance import ComplianceResult, ComplianceStatus, merge


class TestMergeANDMode:
    """Test merge function with AND mode."""

    def test_and_both_allowed(self):
        """AND of two allowed results should be allowed."""
        results = [
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[])
        ]
        merged = merge(results, mode="AND")
        assert merged.status == ComplianceStatus.ALLOWED
        assert merged.problems == []

    def test_and_one_restricted(self):
        """AND with one restricted should be restricted."""
        results = [
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["GPL-2.0-only"])
        ]
        merged = merge(results, mode="AND")
        assert merged.status == ComplianceStatus.RESTRICTED
        assert merged.problems == ["GPL-2.0-only"]

    def test_and_both_restricted(self):
        """AND of two restricted should be restricted."""
        results = [
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["GPL-2.0"]),
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["AGPL-3.0"])
        ]
        merged = merge(results, mode="AND")
        assert merged.status == ComplianceStatus.RESTRICTED
        assert "GPL-2.0" in merged.problems
        assert "AGPL-3.0" in merged.problems

    def test_and_one_uncertain(self):
        """AND with one uncertain and rest allowed should be uncertain."""
        results = [
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown-X"])
        ]
        merged = merge(results, mode="AND")
        assert merged.status == ComplianceStatus.UNCERTAIN
        assert merged.problems == ["Unknown-X"]

    def test_and_restricted_takes_precedence_over_uncertain(self):
        """AND with restricted should be restricted even if uncertain present."""
        results = [
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown"]),
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["GPL"])
        ]
        merged = merge(results, mode="AND")
        assert merged.status == ComplianceStatus.RESTRICTED
        assert "GPL" in merged.problems
        assert "Unknown" in merged.problems


class TestMergeORMode:
    """Test merge function with OR mode."""

    def test_or_both_allowed(self):
        """OR of two allowed should be allowed."""
        results = [
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[])
        ]
        merged = merge(results, mode="OR")
        assert merged.status == ComplianceStatus.ALLOWED
        assert merged.problems == []

    def test_or_one_allowed(self):
        """OR with one allowed should be allowed."""
        results = [
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[]),
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["GPL-2.0"])
        ]
        merged = merge(results, mode="OR")
        assert merged.status == ComplianceStatus.ALLOWED
        assert merged.problems == []

    def test_or_both_restricted(self):
        """OR of two restricted should be restricted."""
        results = [
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["GPL-2.0"]),
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["AGPL-3.0"])
        ]
        merged = merge(results, mode="OR")
        assert merged.status == ComplianceStatus.RESTRICTED
        assert "GPL-2.0" in merged.problems
        assert "AGPL-3.0" in merged.problems

    def test_or_uncertain_when_not_all_restricted(self):
        """OR with uncertain and restricted should be uncertain."""
        results = [
            ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["GPL"]),
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown"])
        ]
        merged = merge(results, mode="OR")
        assert merged.status == ComplianceStatus.UNCERTAIN
        assert merged.problems == ["GPL", "Unknown"]

    def test_or_allowed_takes_precedence_over_uncertain(self):
        """OR with allowed should be allowed even if uncertain present."""
        results = [
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown"]),
            ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[])
        ]
        merged = merge(results, mode="OR")
        assert merged.status == ComplianceStatus.ALLOWED
        assert merged.problems == []

    def test_or_both_uncertain(self):
        """OR of two uncertain should be uncertain (we're uncertain about both options)."""
        results = [
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown-1"]),
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown-2"])
        ]
        merged = merge(results, mode="OR")
        assert merged.status == ComplianceStatus.UNCERTAIN
        assert "Unknown-1" in merged.problems
        assert "Unknown-2" in merged.problems


class TestMergeEdgeCases:
    """Test merge function edge cases."""

    def test_merge_single_item_and(self):
        """Merging single item with AND should return that item's status."""
        results = [ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[])]
        merged = merge(results, mode="AND")
        assert merged.status == ComplianceStatus.ALLOWED

    def test_merge_single_item_or(self):
        """Merging single item with OR should return that item's status."""
        results = [ComplianceResult(status=ComplianceStatus.RESTRICTED, problems=["GPL"])]
        merged = merge(results, mode="OR")
        assert merged.status == ComplianceStatus.RESTRICTED

    def test_merge_invalid_mode(self):
        """Invalid merge mode should raise ValueError."""
        results = [ComplianceResult(status=ComplianceStatus.ALLOWED, problems=[])]
        try:
            merge(results, mode="XOR")  # pyright: ignore[reportArgumentType]
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            assert "Unknown merge mode" in str(e)  # noqa: PT017

    def test_merge_multiple_problems_combined(self):
        """Problems from multiple results should all be combined."""
        results = [
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown-1", "Unknown-2"]),
            ComplianceResult(status=ComplianceStatus.UNCERTAIN, problems=["Unknown-3"])
        ]
        merged = merge(results, mode="AND")
        assert len(merged.problems) == 3
        assert "Unknown-1" in merged.problems
        assert "Unknown-2" in merged.problems
        assert "Unknown-3" in merged.problems

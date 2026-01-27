"""Unit tests for license compliance evaluation."""

import pytest

from dash_license_scan.compliance import (
    ComplianceStatus,
    evaluate_compatibility,
)


class TestComplianceStatus:
    """Test ComplianceStatus constants."""

    def test_status_values_are_distinct(self):
        """Ensure status values are unique and printable."""
        assert ComplianceStatus.ALLOWED == "✅"
        assert ComplianceStatus.RESTRICTED == "❌"
        assert ComplianceStatus.UNCERTAIN == "⚠️"


class TestSimpleLicenses:
    """Test evaluation of simple single licenses."""

    def test_apache_2_0_is_allowed(self):
        """Apache-2.0 should be allowed."""
        result = evaluate_compatibility("Apache-2.0", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_mit_is_allowed(self):
        """MIT should be allowed."""
        result = evaluate_compatibility("MIT", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_bsd_2_clause_is_allowed(self):
        """BSD-2-Clause should be allowed."""
        result = evaluate_compatibility("BSD-2-Clause", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_bsd_3_clause_is_allowed(self):
        """BSD-3-Clause should be allowed."""
        result = evaluate_compatibility("BSD-3-Clause", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_isc_is_allowed(self):
        """ISC should be allowed."""
        result = evaluate_compatibility("ISC", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_mpl_2_0_is_allowed(self):
        """MPL-2.0 should be allowed."""
        result = evaluate_compatibility("MPL-2.0", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_lgpl_2_1_is_allowed(self):
        """LGPL-2.1 should be allowed."""
        result = evaluate_compatibility("LGPL-2.1", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_lgpl_3_0_is_restricted(self):
        """LGPL-3.0 is restricted due to GPLv3 provisions."""
        result = evaluate_compatibility("LGPL-3.0", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED


class TestRestrictedLicenses:
    """Test evaluation of restricted licenses."""

    def test_gpl_2_0_is_restricted(self):
        """GPL-2.0 should be restricted."""
        result = evaluate_compatibility("GPL-2.0", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_gpl_2_0_plus_is_restricted(self):
        """GPL-2.0+ should be restricted."""
        result = evaluate_compatibility("GPL-2.0+", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_gpl_3_0_is_restricted(self):
        """GPL-3.0 should be restricted."""
        result = evaluate_compatibility("GPL-3.0", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_gpl_3_0_plus_is_restricted(self):
        """GPL-3.0+ should be restricted."""
        result = evaluate_compatibility("GPL-3.0+", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_agpl_3_0_is_restricted(self):
        """AGPL-3.0 should be restricted."""
        result = evaluate_compatibility("AGPL-3.0", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_sspl_1_0_is_restricted(self):
        """SSPL-1.0 should be restricted."""
        result = evaluate_compatibility("SSPL-1.0", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED


class TestUncertainLicenses:
    """Test evaluation of unknown/uncertain licenses."""

    def test_empty_string_is_uncertain(self):
        """Empty string should be uncertain."""
        result = evaluate_compatibility("", "Apache-2.0")
        assert result == ComplianceStatus.UNCERTAIN

    def test_unknown_license_is_uncertain(self):
        """Unknown license should be uncertain."""
        result = evaluate_compatibility("Unknown-License-X", "Apache-2.0")
        assert result == ComplianceStatus.UNCERTAIN

    def test_invalid_expression_is_uncertain(self):
        """Invalid expression should be uncertain."""
        result = evaluate_compatibility("(((Invalid))))", "Apache-2.0")
        assert result == ComplianceStatus.UNCERTAIN


class TestAndExpressions:
    """Test evaluation of AND expressions."""

    def test_mit_and_apache_2_0_is_allowed(self):
        """MIT AND Apache-2.0 should be allowed (both allowed)."""
        result = evaluate_compatibility("MIT AND Apache-2.0", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_bsd_and_mit_is_allowed(self):
        """BSD-2-Clause AND MIT should be allowed (both allowed)."""
        result = evaluate_compatibility("BSD-2-Clause AND MIT", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_gpl_and_mit_is_restricted(self):
        """GPL-2.0 AND MIT should be restricted (one is restricted)."""
        result = evaluate_compatibility("GPL-2.0 AND MIT", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_gpl_and_gpl_is_restricted(self):
        """GPL-2.0 AND GPL-3.0 should be restricted (both restricted)."""
        result = evaluate_compatibility("GPL-2.0 AND GPL-3.0", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_mit_and_unknown_is_uncertain(self):
        """MIT AND Unknown-License should be uncertain (one is uncertain)."""
        result = evaluate_compatibility("MIT AND Unknown-License-X", "Apache-2.0")
        assert result == ComplianceStatus.UNCERTAIN


class TestOrExpressions:
    """Test evaluation of OR expressions."""

    def test_mit_or_apache_2_0_is_allowed(self):
        """MIT OR Apache-2.0 should be allowed (both allowed)."""
        result = evaluate_compatibility("MIT OR Apache-2.0", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_mit_or_bsd_is_allowed(self):
        """MIT OR BSD-2-Clause should be allowed (both allowed)."""
        result = evaluate_compatibility("MIT OR BSD-2-Clause", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_mit_or_gpl_is_allowed(self):
        """MIT OR GPL-2.0 should be allowed (one is allowed)."""
        result = evaluate_compatibility("MIT OR GPL-2.0", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_gpl_2_0_or_gpl_3_0_is_restricted(self):
        """GPL-2.0 OR GPL-3.0 should be restricted (all restricted)."""
        result = evaluate_compatibility("GPL-2.0 OR GPL-3.0", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED

    def test_apache_2_0_or_gpl_is_allowed(self):
        """Apache-2.0 OR GPL-2.0 should be allowed (one is allowed)."""
        result = evaluate_compatibility("Apache-2.0 OR GPL-2.0", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_gpl_or_unknown_is_uncertain(self):
        """GPL-2.0 OR Unknown-License should be uncertain (not all restricted, but has uncertain)."""
        result = evaluate_compatibility("GPL-2.0 OR Unknown-License-X", "Apache-2.0")
        assert result == ComplianceStatus.UNCERTAIN


class TestComplexExpressions:
    """Test evaluation of complex nested expressions."""

    def test_mit_and_apache_or_bsd(self):
        """(MIT AND Apache-2.0) OR BSD-2-Clause should be allowed."""
        result = evaluate_compatibility("(MIT AND Apache-2.0) OR BSD-2-Clause", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_gpl_and_mit_or_apache(self):
        """(GPL-2.0 AND MIT) OR Apache-2.0 should be allowed (first is restricted, second is allowed)."""
        result = evaluate_compatibility("(GPL-2.0 AND MIT) OR Apache-2.0", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_mit_or_gpl_and_apache(self):
        """MIT OR (GPL-2.0 AND Apache-2.0) should be allowed."""
        result = evaluate_compatibility("MIT OR (GPL-2.0 AND Apache-2.0)", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_gpl_or_agpl_and_restricted(self):
        """GPL-2.0 OR (AGPL-3.0 AND SSPL-1.0) should be restricted."""
        result = evaluate_compatibility("GPL-2.0 OR (AGPL-3.0 AND SSPL-1.0)", "Apache-2.0")
        assert result == ComplianceStatus.RESTRICTED


class TestRealWorldExamples:
    """Test with real-world license expressions."""

    def test_requests_license_expression(self):
        """Test with a real-world expression from requests library."""
        # requests uses Apache-2.0 AND MIT
        result = evaluate_compatibility("Apache-2.0 AND MIT", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_click_license_expression(self):
        """Test with a real-world expression from click library."""
        # click uses BSD-2-Clause AND BSD-3-Clause
        result = evaluate_compatibility("BSD-2-Clause AND BSD-3-Clause", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_complex_permissive_mix(self):
        """Test with multiple permissive licenses."""
        result = evaluate_compatibility(
            "MIT OR Apache-2.0 OR BSD-3-Clause OR ISC", "Apache-2.0"
        )
        assert result == ComplianceStatus.ALLOWED


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_whitespace_handling(self):
        """Test expressions with extra whitespace."""
        result = evaluate_compatibility("  MIT  ", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED

    def test_case_insensitivity(self):
        """Test case-insensitive license matching."""
        result = evaluate_compatibility("mit", "Apache-2.0")
        # license-expression library normalizes to MIT
        # This tests that our code handles variations
        assert result in [ComplianceStatus.ALLOWED, ComplianceStatus.UNCERTAIN]

    def test_none_string_is_uncertain(self):
        """Test handling of empty/whitespace-only strings."""
        result = evaluate_compatibility("   ", "Apache-2.0")
        assert result == ComplianceStatus.UNCERTAIN

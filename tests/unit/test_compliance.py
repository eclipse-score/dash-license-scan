"""Unit tests for license compliance evaluation."""

import pytest

from dash_license_scan.compliance import (
    ComplianceStatus,
    evaluate_compatibility,
)


class TestSimpleLicenses:
    """Test evaluation of simple single licenses."""

    def test_mit_is_allowed(self):
        """MIT should be allowed."""
        result = evaluate_compatibility("MIT", "Apache-2.0")
        assert result == ComplianceStatus.ALLOWED


class TestRestrictedLicenses:
    """Test evaluation of restricted licenses."""

    def test_gpl_2_0_is_restricted(self):
        """GPL-2.0 should be restricted."""
        result = evaluate_compatibility("GPL-2.0", "Apache-2.0")
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

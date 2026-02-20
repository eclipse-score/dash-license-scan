"""Unit tests for license compliance evaluation."""

from dash_license_scan.compliance import (
    ComplianceStatus,
    evaluate_compatibility,
)


def test_mit_is_allowed():
    """MIT should be allowed."""
    actual_outcome = evaluate_compatibility("MIT", "ASF")
    assert actual_outcome.status == ComplianceStatus.ALLOWED


def test_gpl_2_0_is_restricted():
    """GPL-2.0-only should be restricted."""
    actual_outcome = evaluate_compatibility("GPL-2.0-only", "ASF")
    assert actual_outcome.status == ComplianceStatus.RESTRICTED


def test_empty_string_is_restricted():
    """Empty string should be restricted (no license = no use)."""
    actual_outcome = evaluate_compatibility("", "ASF")
    assert actual_outcome.status == ComplianceStatus.RESTRICTED


def test_unknown_license_is_uncertain():
    """Unknown license should be uncertain."""
    actual_outcome = evaluate_compatibility("Unknown-License-X", "ASF")
    assert actual_outcome.status == ComplianceStatus.UNCERTAIN


def test_invalid_expression_is_uncertain():
    """Invalid expressions are not allowed at all."""
    actual_outcome = evaluate_compatibility("(((Invalid))))", "ASF")
    assert actual_outcome.status == ComplianceStatus.RESTRICTED


def test_bsd_and_mit_is_allowed():
    """BSD-2-Clause AND MIT should be allowed (both allowed)."""
    actual_outcome = evaluate_compatibility("BSD-2-Clause AND MIT", "ASF")
    assert actual_outcome.status == ComplianceStatus.ALLOWED


def test_gpl_and_mit_is_restricted():
    """GPL-2.0-only AND MIT should be restricted (one is restricted)."""
    actual_outcome = evaluate_compatibility("GPL-2.0-only AND MIT", "ASF")
    assert actual_outcome.status == ComplianceStatus.RESTRICTED


def test_gpl_and_gpl_is_restricted():
    """GPL-2.0-only AND GPL-3.0-only should be restricted (both restricted)."""
    actual_outcome = evaluate_compatibility("GPL-2.0-only AND GPL-3.0-only", "ASF")
    assert actual_outcome.status == ComplianceStatus.RESTRICTED


def test_mit_and_unknown_is_uncertain():
    """MIT AND Unknown-License should be uncertain (one is uncertain)."""
    actual_outcome = evaluate_compatibility("MIT AND Unknown-License-X", "ASF")
    assert actual_outcome.status == ComplianceStatus.UNCERTAIN


def test_mit_or_bsd_is_allowed():
    """MIT OR BSD-2-Clause should be allowed (both allowed)."""
    actual_outcome = evaluate_compatibility("MIT OR BSD-2-Clause", "ASF")
    assert actual_outcome.status == ComplianceStatus.ALLOWED


def test_mit_or_gpl_is_allowed():
    """MIT OR GPL-2.0-only should be allowed (one is allowed)."""
    actual_outcome = evaluate_compatibility("MIT OR GPL-2.0-only", "ASF")
    assert actual_outcome.status == ComplianceStatus.ALLOWED


def test_gpl_2_0_or_gpl_3_0_is_restricted():
    """GPL-2.0-only OR GPL-3.0-only should be restricted (all restricted)."""
    actual_outcome = evaluate_compatibility("GPL-2.0-only OR GPL-3.0-only", "ASF")
    assert actual_outcome.status == ComplianceStatus.RESTRICTED


def test_gpl_or_unknown_is_uncertain():
    """GPL-2.0-only OR Unknown-License should be uncertain (not all restricted, but has uncertain)."""
    actual_outcome = evaluate_compatibility("GPL-2.0-only OR Unknown-License-X", "ASF")
    assert actual_outcome.status == ComplianceStatus.UNCERTAIN


def test_mit_and_apache_or_bsd():
    """(MIT AND Apache-2.0) OR BSD-2-Clause should be allowed."""
    actual_outcome = evaluate_compatibility(
        "(MIT AND Apache-2.0) OR BSD-2-Clause", "ASF"
    )
    assert actual_outcome.status == ComplianceStatus.ALLOWED


def test_gpl_and_mit_or_apache():
    """(GPL-2.0-only AND MIT) OR Apache-2.0 should be allowed (first is restricted, second is allowed)."""
    actual_outcome = evaluate_compatibility(
        "(GPL-2.0-only AND MIT) OR Apache-2.0", "ASF"
    )
    assert actual_outcome.status == ComplianceStatus.ALLOWED


def test_mit_or_gpl_and_apache():
    """MIT OR (GPL-2.0-only AND Apache-2.0) should be allowed."""
    actual_outcome = evaluate_compatibility(
        "MIT OR (GPL-2.0-only AND Apache-2.0)", "ASF"
    )
    assert actual_outcome.status == ComplianceStatus.ALLOWED


def test_gpl_or_agpl_and_restricted():
    """GPL-2.0-only OR (AGPL-3.0 AND SSPL-1.0) should be restricted."""
    actual_outcome = evaluate_compatibility(
        "GPL-2.0-only OR (AGPL-3.0 AND SSPL-1.0)", "ASF"
    )
    assert actual_outcome.status == ComplianceStatus.RESTRICTED

"""Unit tests for license compliance evaluation."""

from dash_license_scan.compliance import (
    ComplianceStatus,
    evaluate_compatibility,
)

# Next steps:
# - idea: can we generate a markdown table from all these tests automatically?
# - confirm AND and OR behavior with license experts
# - improve `_eval` code (e.g. comments, type-safety, ....)
# - update REAADME on how to use as an action
# - auto discovery of lock files (e.g. **/requirements.txt), see how dependabot does it!
# - ping eclipse whether they want to have this tool
# - improve comment formatting etc on PR (e.g. merge last three columns)
# - setup pypi releases
# - remove dash from tooling repo
# - adjust cicd-workflows license-check.yml to call this action instead of bazel crap
# - confirm whether "ASF 3rd Party License Policy" grouping applies to S-CORE restrictions and distributor restrictions
#   -> check against ETAS policy --> Alex, Aravind, Sebouh?, Anastasia?
# - follow up on https://gitlab.eclipse.org/eclipsefdn/emo-team/iplab/-/issues/19880 (drop GPL?)
# - follow up on https://gitlab.eclipse.org/eclipsefdn/emo-team/iplab/-/issues/24455 (PyGithub approved with GPL3)
# pypi remove optional dependency [braket], e.g. sphinx[plotting] -> sphinx


def test_mit_is_allowed():
    """MIT should be allowed."""
    assert evaluate_compatibility("MIT", "Apache-2.0") == ComplianceStatus.ALLOWED


def test_gpl_2_0_is_restricted():
    """GPL-2.0-only should be restricted."""
    assert (
        evaluate_compatibility("GPL-2.0-only", "Apache-2.0")
        == ComplianceStatus.RESTRICTED
    )


def test_empty_string_is_restricted():
    """Empty string should be restricted (no license = no use)."""
    assert evaluate_compatibility("", "Apache-2.0") == ComplianceStatus.RESTRICTED


def test_unknown_license_is_uncertain():
    """Unknown license should be uncertain."""
    assert (
        evaluate_compatibility("Unknown-License-X", "Apache-2.0")
        == ComplianceStatus.UNCERTAIN
    )


def test_invalid_expression_is_uncertain():
    """Invalid expressions are not allowed at all."""
    assert (
        evaluate_compatibility("(((Invalid))))", "Apache-2.0")
        == ComplianceStatus.RESTRICTED
    )


def test_bsd_and_mit_is_allowed():
    """BSD-2-Clause AND MIT should be allowed (both allowed)."""
    assert (
        evaluate_compatibility("BSD-2-Clause AND MIT", "Apache-2.0")
        == ComplianceStatus.ALLOWED
    )


def test_gpl_and_mit_is_restricted():
    """GPL-2.0-only AND MIT should be restricted (one is restricted)."""
    assert (
        evaluate_compatibility("GPL-2.0-only AND MIT", "Apache-2.0")
        == ComplianceStatus.RESTRICTED
    )


def test_gpl_and_gpl_is_restricted():
    """GPL-2.0-only AND GPL-3.0-only should be restricted (both restricted)."""
    assert (
        evaluate_compatibility("GPL-2.0-only AND GPL-3.0-only", "Apache-2.0")
        == ComplianceStatus.RESTRICTED
    )


def test_mit_and_unknown_is_uncertain():
    """MIT AND Unknown-License should be uncertain (one is uncertain)."""
    assert (
        evaluate_compatibility("MIT AND Unknown-License-X", "Apache-2.0")
        == ComplianceStatus.UNCERTAIN
    )


def test_mit_or_bsd_is_allowed():
    """MIT OR BSD-2-Clause should be allowed (both allowed)."""
    assert (
        evaluate_compatibility("MIT OR BSD-2-Clause", "Apache-2.0")
        == ComplianceStatus.ALLOWED
    )


def test_mit_or_gpl_is_allowed():
    """MIT OR GPL-2.0-only should be allowed (one is allowed)."""
    assert (
        evaluate_compatibility("MIT OR GPL-2.0-only", "Apache-2.0")
        == ComplianceStatus.ALLOWED
    )


def test_gpl_2_0_or_gpl_3_0_is_restricted():
    """GPL-2.0-only OR GPL-3.0-only should be restricted (all restricted)."""
    assert (
        evaluate_compatibility("GPL-2.0-only OR GPL-3.0-only", "Apache-2.0")
        == ComplianceStatus.RESTRICTED
    )


def test_gpl_or_unknown_is_uncertain():
    """GPL-2.0-only OR Unknown-License should be uncertain (not all restricted, but has uncertain)."""
    assert (
        evaluate_compatibility("GPL-2.0-only OR Unknown-License-X", "Apache-2.0")
        == ComplianceStatus.UNCERTAIN
    )


def test_mit_and_apache_or_bsd():
    """(MIT AND Apache-2.0) OR BSD-2-Clause should be allowed."""
    assert (
        evaluate_compatibility("(MIT AND Apache-2.0) OR BSD-2-Clause", "Apache-2.0")
        == ComplianceStatus.ALLOWED
    )


def test_gpl_and_mit_or_apache():
    """(GPL-2.0-only AND MIT) OR Apache-2.0 should be allowed (first is restricted, second is allowed)."""
    assert (
        evaluate_compatibility("(GPL-2.0-only AND MIT) OR Apache-2.0", "Apache-2.0")
        == ComplianceStatus.ALLOWED
    )


def test_mit_or_gpl_and_apache():
    """MIT OR (GPL-2.0-only AND Apache-2.0) should be allowed."""
    assert (
        evaluate_compatibility("MIT OR (GPL-2.0-only AND Apache-2.0)", "Apache-2.0")
        == ComplianceStatus.ALLOWED
    )


def test_gpl_or_agpl_and_restricted():
    """GPL-2.0-only OR (AGPL-3.0 AND SSPL-1.0) should be restricted."""
    assert (
        evaluate_compatibility("GPL-2.0-only OR (AGPL-3.0 AND SSPL-1.0)", "Apache-2.0")
        == ComplianceStatus.RESTRICTED
    )

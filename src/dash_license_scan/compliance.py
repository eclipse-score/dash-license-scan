"""License compliance evaluation logic.

Evaluate SPDX license expressions (AND/OR/parentheses) against a target policy.

Currently supported:
- --comply-with Apache-2.0
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from functools import cache
from importlib import resources
from logging import getLogger
from typing import Any, Literal

from license_expression import ExpressionError, Licensing

log = getLogger(__name__)


class ComplianceStatus(Enum):
    """Tri-state compliance result (intended for Markdown output)."""

    ALLOWED = "✅"
    RESTRICTED = "❌"
    UNCERTAIN = "⚠️"  # unknown / conditional / parse errors / LicenseRef-*

    def __str__(self) -> str:
        return self.value


@dataclass
class ComplianceResult:
    status: ComplianceStatus
    problems: list[str]


def merge(
    values: list[ComplianceResult], mode: Literal["AND", "OR"]
) -> ComplianceResult:
    if mode == "AND":
        status = ComplianceStatus.ALLOWED
        problems = []
        for v in values:
            if v.status == ComplianceStatus.RESTRICTED:
                status = ComplianceStatus.RESTRICTED
            elif (
                v.status == ComplianceStatus.UNCERTAIN
                and status != ComplianceStatus.RESTRICTED
            ):
                status = ComplianceStatus.UNCERTAIN
            problems.extend(v.problems)
        return ComplianceResult(status=status, problems=problems)
    elif mode == "OR":
        status = ComplianceStatus.RESTRICTED
        problems = []
        for v in values:
            if v.status == ComplianceStatus.ALLOWED:
                status = ComplianceStatus.ALLOWED
            elif (
                v.status == ComplianceStatus.UNCERTAIN
                and status != ComplianceStatus.ALLOWED
            ):
                status = ComplianceStatus.UNCERTAIN
            problems.extend(v.problems)
        # Clear problems if result is ALLOWED (one option is fine)
        if status == ComplianceStatus.ALLOWED:
            problems = []
        return ComplianceResult(status=status, problems=problems)
    else:
        raise ValueError(f"Unknown merge mode: {mode}")


@cache
def _load_policies_json() -> dict[str, Any]:
    """Load license policies from JSON resource file."""
    try:
        policy_file = (
            resources.files("dash_license_scan.resources") / "license_policies.json"
        )
        return json.loads(policy_file.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to load license policies: %s", e)
        raise SystemExit(2) from e


@dataclass
class Policy:
    allowed: set[str]
    restricted: set[str]


@cache
def _get_policy(policy_name: str) -> Policy:
    data = _load_policies_json()
    try:
        pol = data[policy_name]
    except KeyError:
        log.error("License policy %r not found", policy_name)
        log.info("Available policies: %s", ", ".join(data.keys()))
        raise SystemExit(2) from None

    if not isinstance(pol, dict):
        raise ValueError("Malformed license policies data")

    allowed = pol.get("allowed", [])  # pyright: ignore[reportUnknownVariableType]
    restricted = pol.get("restricted", [])  # pyright: ignore[reportUnknownVariableType]

    if not isinstance(allowed, list) or not isinstance(restricted, list):
        raise ValueError("Malformed license policies data")

    # SPDX IDs are expected to be exact strings.
    return Policy(allowed=set(allowed), restricted=set(restricted))


def _load_policies(names: str | list[str]) -> dict[str, Policy]:
    """Load one or more license policies by name."""
    if isinstance(names, str):
        names = [names]

    policies: dict[str, Policy] = {}
    for name in names:
        policies[name] = _get_policy(name)

    return policies


def _merge_policies(policies: list[Policy]) -> Policy:
    return Policy(
        allowed=set.intersection(*(p.allowed for p in policies)),
        restricted=set.union(*(p.restricted for p in policies)),
    )


def _eval(expr: object, policy: Policy) -> ComplianceResult:
    """Recursively evaluate a parsed license-expression AST node."""
    # Leaf: license symbol (e.g. MIT, Apache-2.0, LicenseRef-...)
    key = getattr(expr, "key", None)
    if isinstance(key, str):
        if key in policy.restricted:
            return ComplianceResult(ComplianceStatus.RESTRICTED, problems=[key])
        if key in policy.allowed:
            return ComplianceResult(ComplianceStatus.ALLOWED, problems=[])
        return ComplianceResult(ComplianceStatus.UNCERTAIN, problems=[key])

    # Some nodes represent "License WITH Exception", these are currently not supported.
    license_symbol = getattr(expr, "license_symbol", None)
    if license_symbol is not None:
        return ComplianceResult(ComplianceStatus.UNCERTAIN, problems=[str(expr)])

    # Operator nodes: AND/OR with args
    if operator := getattr(expr, "operator", "").strip():
        args = getattr(expr, "args", None)
        if not args:
            log.warning("Error in license expression: %r", expr)
            return ComplianceResult(ComplianceStatus.UNCERTAIN, problems=[str(expr)])

        if operator == "AND":
            results = [_eval(a, policy=policy) for a in args]
            return merge(results, mode="AND")

        if operator == "OR":
            results = [_eval(a, policy=policy) for a in args]
            return merge(results, mode="OR")

        log.warning(f"Unknown operator '{operator}' in license expression: {expr}")
        return ComplianceResult(ComplianceStatus.UNCERTAIN, problems=[str(expr)])

    log.warning("Unknown license expression: %r", expr)
    return ComplianceResult(ComplianceStatus.UNCERTAIN, problems=[str(expr)])


def _parse_license_expression(license_expression: str) -> object | None:
    """Parse an SPDX license expression into an AST node."""
    licensing = Licensing()
    try:
        return licensing.parse(license_expression)
    except ExpressionError:
        log.warning("Failed to parse license expression: %r", license_expression)
        return None


def evaluate_compatibility(
    license_expression: str, policy: str | list[str]
) -> ComplianceResult:
    """Evaluate if an SPDX license expression complies with a policy.

    Args:
        license_expression: SPDX expression (already sanitized upstream).
        policy: one or more policy names (e.g., "ASF", "EF")

    Returns:
        ComplianceStatus.ALLOWED / RESTRICTED / UNCERTAIN
    """

    policies = _load_policies(policy)
    combined_policy = _merge_policies(list(policies.values()))

    parsed = _parse_license_expression(license_expression)
    if parsed is None:
        return ComplianceResult(
            ComplianceStatus.RESTRICTED, problems=[license_expression]
        )

    return _eval(parsed, combined_policy)

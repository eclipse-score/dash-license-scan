"""License compliance evaluation logic.

Evaluate SPDX license expressions (AND/OR/parentheses) against a target policy.

Currently supported:
- --comply-with Apache-2.0
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib import resources
from logging import getLogger
from typing import Any

from license_expression import ExpressionError, Licensing

log = getLogger(__name__)


class ComplianceStatus:
    """Tri-state compliance result (intended for Markdown output)."""

    ALLOWED = "✅"
    RESTRICTED = "❌"
    UNCERTAIN = "⚠️"  # unknown / conditional / parse errors / LicenseRef-*


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
    if policy_name != "Apache-2.0":
        raise ValueError(
            f"Unsupported value for --comply-with: {policy_name!r}. Supported: Apache-2.0"
        )

    data = _load_policies_json()
    pol = data.get(policy_name)
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


def _eval(expr: object, policy: Policy) -> str:
    """Recursively evaluate a parsed license-expression AST node."""
    # Leaf: license symbol (e.g. MIT, Apache-2.0, LicenseRef-...)
    key = getattr(expr, "key", None)
    if isinstance(key, str):
        if key in policy.restricted:
            return ComplianceStatus.RESTRICTED
        if key in policy.allowed:
            return ComplianceStatus.ALLOWED
        return ComplianceStatus.UNCERTAIN

    # Some nodes represent "License WITH Exception"
    license_symbol = getattr(expr, "license_symbol", None)
    if license_symbol is not None:
        base_key = getattr(license_symbol, "key", None)
        if isinstance(base_key, str):
            if base_key in policy.restricted:
                return ComplianceStatus.RESTRICTED
            if base_key in policy.allowed:
                return ComplianceStatus.ALLOWED
        return ComplianceStatus.UNCERTAIN

    # Operator nodes: AND/OR with args
    operator = getattr(expr, "operator", None)
    args = getattr(expr, "args", None)

    if isinstance(operator, str) and isinstance(args, tuple):
        op = operator.strip().upper()

        if op == "AND":
            results = [_eval(a, policy=policy) for a in args]
            if ComplianceStatus.RESTRICTED in results:
                return ComplianceStatus.RESTRICTED
            if all(r == ComplianceStatus.ALLOWED for r in results):
                return ComplianceStatus.ALLOWED
            return ComplianceStatus.UNCERTAIN

        if op == "OR":
            results = [_eval(a, policy=policy) for a in args]
            if ComplianceStatus.ALLOWED in results:
                return ComplianceStatus.ALLOWED
            if all(r == ComplianceStatus.RESTRICTED for r in results):
                return ComplianceStatus.RESTRICTED
            return ComplianceStatus.UNCERTAIN

        else:
            log.debug("Unknown operator in license expression: %r", operator)
            return ComplianceStatus.UNCERTAIN

    return ComplianceStatus.UNCERTAIN


def _parse_license_expression(license_expression: str) -> object | None:
    """Parse an SPDX license expression into an AST node."""
    licensing = Licensing()
    try:
        return licensing.parse(license_expression)
    except ExpressionError:
        log.warning("Failed to parse license expression: %r", license_expression)
        return None


def evaluate_compatibility(license_expression: str, policy: str | list[str]) -> str:
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
        return ComplianceStatus.RESTRICTED

    return _eval(parsed, combined_policy)

"""End-to-end CLI tests using the ProductTestKit harness.

Principles: intent-revealing, fast, isolated from external Java, and covering
the key user-visible behaviors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conftest import ProductTestKit


def test_scans_requirements_success(product_test_kit: ProductTestKit):
    summary = """pkg, MIT, approved, clearlydefined
other, Apache-2.0, approved, clearlydefined"""
    product_test_kit.set_fake_jar_response(0, summary)

    dep_file = product_test_kit.fake_requirements_file(["pkg==1.0.0", "other==2.0.0"])

    exit_code = product_test_kit.run([str(dep_file)])
    assert exit_code == 0

    out = product_test_kit.stdout
    assert "# Dash License Scan" in out
    assert "| Package | License | Status | Details |" in out
    assert "pkg" in out
    assert "other" in out
    assert product_test_kit.jar_cmd is not None
    assert "pypi/pypi/-/pkg/1.0.0" in (product_test_kit.jar_input or "")
    assert "pypi/pypi/-/other/2.0.0" in (product_test_kit.jar_input or "")


def test_review_requires_env(product_test_kit: ProductTestKit):
    product_test_kit.set_fake_jar_response(0, "SHOULD_NOT_RUN")
    product_test_kit.monkeypatch.delenv("ECLIPSE_PROJECT", raising=False)
    product_test_kit.monkeypatch.delenv("DASH_TOKEN", raising=False)
    product_test_kit.monkeypatch.delenv("ECLIPSE_GITLAB_API_TOKEN", raising=False)

    dep_file = product_test_kit.fake_requirements_file(["pkg==1.0.0"])

    exit_code = product_test_kit.run(["--trigger-review", str(dep_file)])
    assert exit_code == 2


def test_dry_run_prints_command_and_dependencies(product_test_kit: ProductTestKit):
    dep_file = product_test_kit.fake_requirements_file(["pkg==1.0.0", "other==2.0.0"])

    exit_code = product_test_kit.run(["--dry-run", str(dep_file)])
    assert exit_code == 0

    out = product_test_kit.stdout
    assert "Would run command: java" in out
    assert "-jar /fake/jar.jar" in out or "-jar \\fake\\jar.jar" in out
    assert "With dependencies:" in out
    assert "pypi/pypi/-/pkg/1.0.0" in out
    assert "pypi/pypi/-/other/2.0.0" in out


def test_empty_lockfile_returns_error(product_test_kit: ProductTestKit):
    dep_file = product_test_kit.fake_requirements_file([])

    exit_code = product_test_kit.run([str(dep_file)])
    assert exit_code == 2

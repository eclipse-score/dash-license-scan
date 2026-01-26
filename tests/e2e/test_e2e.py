"""End-to-end CLI tests using the ProductTestKit harness.

Principles: intent-revealing, fast, isolated from external Java, and covering
the key user-visible behaviors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conftest import ProductTestKit


def test_scans_requirements_success(product_test_kit: ProductTestKit):
    cli = product_test_kit
    cli.set_fake_jar_response(0, "SUMMARY OK")

    dep_file = cli.fake_requirements_file(["pkg==1.0.0", "other==2.0.0"])

    exit_code = cli.run([str(dep_file)])
    assert exit_code == 0

    out = cli.stdout
    assert "# Dash License Scan: ✅ No issues found" in out
    assert "SUMMARY OK" in out
    assert cli.jar_cmd is not None
    assert "pypi/pypi/-/pkg/1.0.0" in (cli.jar_input or "")
    assert "pypi/pypi/-/other/2.0.0" in (cli.jar_input or "")


def test_scans_requirements_with_issues(product_test_kit: ProductTestKit):
    cli = product_test_kit
    cli.set_fake_jar_response(2, "ISSUE SUMMARY", stderr="http://example.com/issue1\nhttp://example.com/issue2")

    dep_file = cli.fake_requirements_file(["bad==0.1", "worse==0.2"])

    exit_code = cli.run([str(dep_file)])
    assert exit_code == 1

    out = cli.stdout
    assert "# Dash License Scan: ❌ 2 Issues found" in out
    assert "ISSUE SUMMARY" in out


def test_review_requires_env(product_test_kit: ProductTestKit):
    cli = product_test_kit
    cli.set_fake_jar_response(0, "SHOULD_NOT_RUN")
    cli.monkeypatch.delenv("ECLIPSE_PROJECT", raising=False)
    cli.monkeypatch.delenv("DASH_TOKEN", raising=False)
    cli.monkeypatch.delenv("ECLIPSE_GITLAB_API_TOKEN", raising=False)

    dep_file = cli.fake_requirements_file(["pkg==1.0.0"])

    exit_code = cli.run(["--trigger-review", str(dep_file)])
    assert exit_code == 1


def test_review_triggers_notice(product_test_kit: ProductTestKit):
    cli = product_test_kit
    cli.set_fake_jar_response(1, "REVIEW SUMMARY", stderr="http://example.com/issue1")
    cli.set_env(project="demo", token="secret")

    dep_file = cli.fake_requirements_file(["pkg==1.0.0"])

    exit_code = cli.run(["--trigger-review", str(dep_file)])
    assert exit_code == 1

    out = cli.stdout
    assert "# Dash License Scan: ❌ 1 Issues found" in out
    assert "REVIEW SUMMARY" in out
    assert "License review process was triggered" in out
    assert "http://example.com/issue1" in out


def test_dry_run_prints_command_and_dependencies(product_test_kit: ProductTestKit):
    cli = product_test_kit

    dep_file = cli.fake_requirements_file(["pkg==1.0.0", "other==2.0.0"])

    exit_code = cli.run(["--dry-run", str(dep_file)])
    assert exit_code == 0

    out = cli.stdout
    assert "Would run command: java" in out
    assert "-jar /fake/jar.jar" in out or "-jar \\fake\\jar.jar" in out
    assert "With dependencies:" in out
    assert "pypi/pypi/-/pkg/1.0.0" in out
    assert "pypi/pypi/-/other/2.0.0" in out


def test_empty_lockfile_returns_error(product_test_kit: ProductTestKit):
    cli = product_test_kit

    dep_file = cli.fake_requirements_file([])

    exit_code = cli.run([str(dep_file)])
    assert exit_code == 2

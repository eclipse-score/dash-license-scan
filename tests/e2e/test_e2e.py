"""End-to-end CLI tests using the ProductTestKit harness.

Principles: intent-revealing, fast, isolated from external Java, and covering
the key user-visible behaviors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conftest import ProductTestKit


def test_scans_requirements_success(product_test_kit: ProductTestKit) -> None:
    cli = product_test_kit
    cli.jar_ok("SUMMARY OK")

    dep_file = cli.write_requirements(["pkg==1.0.0", "other==2.0.0"])

    exit_code = cli.run([str(dep_file)])
    assert exit_code == 0

    out = cli.stdout()
    assert "Scanning 2 dependencies" in out
    assert "Dash Licenses Summary Output: OK" in out
    assert "SUMMARY OK" in out
    assert cli.last_cmd is not None
    assert "pypi/pypi/-/pkg/1.0.0" in (cli.last_input or "")
    assert "pypi/pypi/-/other/2.0.0" in (cli.last_input or "")


def test_scans_requirements_with_issues(product_test_kit: ProductTestKit) -> None:
    cli = product_test_kit
    cli.jar_issues(2, "ISSUE SUMMARY")

    dep_file = cli.write_requirements(["bad==0.1", "worse==0.2"])

    exit_code = cli.run([str(dep_file)])
    assert exit_code == 1

    out = cli.stdout()
    assert "Dash Licenses Summary Output: 2 Issues Found" in out
    assert "ISSUE SUMMARY" in out


def test_review_requires_env(product_test_kit: ProductTestKit) -> None:
    cli = product_test_kit
    cli.jar_ok("SHOULD_NOT_RUN")
    cli.monkeypatch.delenv("ECLIPSE_PROJECT", raising=False)
    cli.monkeypatch.delenv("DASH_TOKEN", raising=False)
    cli.monkeypatch.delenv("ECLIPSE_GITLAB_API_TOKEN", raising=False)

    dep_file = cli.write_requirements(["pkg==1.0.0"])

    exit_code = cli.run(["--review", str(dep_file)])
    assert exit_code == 1


def test_review_triggers_notice(product_test_kit: ProductTestKit) -> None:
    cli = product_test_kit
    cli.jar_issues(1, "REVIEW SUMMARY")
    cli.set_review_env(project="demo", token="secret")

    dep_file = cli.write_requirements(["pkg==1.0.0"])

    exit_code = cli.run(["--review", str(dep_file)])
    assert exit_code == 1

    out = cli.stdout()
    assert "License review process was triggered" in out
    assert "REVIEW SUMMARY" in out


def test_dry_run_prints_command_and_dependencies(product_test_kit: ProductTestKit) -> None:
    cli = product_test_kit

    dep_file = cli.write_requirements(["pkg==1.0.0", "other==2.0.0"])

    exit_code = cli.run(["--dry-run", str(dep_file)])
    assert exit_code == 0

    out = cli.stdout()
    assert "Would run command: java" in out
    assert "-jar /fake/jar.jar" in out
    assert "With dependencies:" in out
    assert "pypi/pypi/-/pkg/1.0.0" in out
    assert "pypi/pypi/-/other/2.0.0" in out


def test_empty_lockfile_returns_error(product_test_kit: ProductTestKit) -> None:
    cli = product_test_kit

    dep_file = cli.write_requirements([])

    exit_code = cli.run([str(dep_file)])
    assert exit_code == 2

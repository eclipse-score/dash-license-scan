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
    assert "| Package | License | Status | Notes |" in out
    assert "pkg" in out
    assert "other" in out
    assert product_test_kit.jar_cmd is not None
    assert "pypi/pypi/-/pkg/1.0.0" in (product_test_kit.jar_input or "")
    assert "pypi/pypi/-/other/2.0.0" in (product_test_kit.jar_input or "")


def test_scans_requirements_with_issues(product_test_kit: ProductTestKit):
    summary = """bad, GPL-2.0-only, restricted, #12345
worse, AGPL-3.0-only, restricted, #12346"""
    product_test_kit.set_fake_jar_response(
        2,
        summary,
        stderr="http://example.com/issue1\nhttp://example.com/issue2",
    )
    product_test_kit.set_env(project="demo", token="secret")

    dep_file = product_test_kit.fake_requirements_file(["bad==0.1", "worse==0.2"])

    exit_code = product_test_kit.run(["--trigger-review", str(dep_file)])
    assert exit_code == 1

    out = product_test_kit.stdout
    assert "# Dash License Scan" in out
    assert "| Package | License | Status | Notes |" in out
    assert "bad" in out
    assert "worse" in out
    assert "## License review process was triggered." in out
    assert "http://example.com/issue1" in out
    assert "http://example.com/issue2" in out


def test_review_requires_env(product_test_kit: ProductTestKit):
    product_test_kit.set_fake_jar_response(0, "SHOULD_NOT_RUN")
    product_test_kit.monkeypatch.delenv("ECLIPSE_PROJECT", raising=False)
    product_test_kit.monkeypatch.delenv("DASH_TOKEN", raising=False)
    product_test_kit.monkeypatch.delenv("ECLIPSE_GITLAB_API_TOKEN", raising=False)

    dep_file = product_test_kit.fake_requirements_file(["pkg==1.0.0"])

    exit_code = product_test_kit.run(["--trigger-review", str(dep_file)])
    assert exit_code == 1


def test_review_triggers_notice(product_test_kit: ProductTestKit):
    summary = "pkg, MIT AND GPL-2.0-only, restricted, #54321"
    product_test_kit.set_fake_jar_response(
        1, summary, stderr="http://example.com/issue1"
    )
    product_test_kit.set_env(project="demo", token="secret")

    dep_file = product_test_kit.fake_requirements_file(["pkg==1.0.0"])

    exit_code = product_test_kit.run(["--trigger-review", str(dep_file)])
    assert exit_code == 1

    out = product_test_kit.stdout
    assert "# Dash License Scan" in out
    assert "| Package | License | Status | Notes |" in out
    assert "pkg" in out
    assert "## License review process was triggered." in out
    assert "http://example.com/issue1" in out


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

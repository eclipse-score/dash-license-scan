"""Unit tests for jar.py utility functions.

Tests focus on edge cases and error handling that provide value beyond e2e tests.
Command construction details are better verified through code review.
"""

from pathlib import Path
from typing import Any

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import dash_license_scan.jar as jar


def test_is_ubuntu_returns_true_when_running_on_ubuntu(fs: FakeFilesystem):
    """Ubuntu detection works by checking /etc/os-release content."""
    fs.create_file("/etc/os-release", contents="NAME=Ubuntu\nID=ubuntu\n")
    assert jar.is_ubuntu()


def test_is_ubuntu_returns_false_when_not_running_on_ubuntu(fs: FakeFilesystem):
    """Non-Ubuntu systems are correctly identified."""
    fs.create_file("/etc/os-release", contents="NAME=Fedora\nID=fedora\n")
    assert not jar.is_ubuntu()


def test_is_ubuntu_returns_false_when_os_release_missing(fs: FakeFilesystem):
    """When /etc/os-release doesn't exist, is_ubuntu() returns False."""
    assert not jar.is_ubuntu()


def test_require_java_succeeds_when_java_is_available(monkeypatch: pytest.MonkeyPatch):
    """When java is on PATH, require_java() completes without error."""
    monkeypatch.setattr(jar.shutil, "which", lambda _: "/usr/bin/java")
    jar.require_java()


def test_require_java_shows_ubuntu_installation_instructions(
    monkeypatch: pytest.MonkeyPatch,
):
    """On Ubuntu systems, helpful apt install command is shown."""
    monkeypatch.setattr(jar.shutil, "which", lambda _: None)
    monkeypatch.setattr(jar, "is_ubuntu", lambda: True)

    with pytest.raises(SystemExit) as exc_info:
        jar.require_java()

    error_message = str(exc_info.value)
    assert "Java runtime not found" in error_message
    assert "apt install openjdk-21-jre-headless" in error_message


def test_require_java_shows_generic_error_on_non_ubuntu(
    monkeypatch: pytest.MonkeyPatch,
):
    """On non-Ubuntu systems, generic installation guidance is provided."""
    monkeypatch.setattr(jar.shutil, "which", lambda _: None)
    monkeypatch.setattr(jar, "is_ubuntu", lambda: False)

    with pytest.raises(SystemExit) as exc_info:
        jar.require_java()

    error_message = str(exc_info.value)
    assert "Java runtime not found" in error_message
    assert "Install a Java 21+ runtime" in error_message
    assert "apt" not in error_message


def test_bundled_jar_returns_valid_path():
    """The bundled JAR file exists and can be accessed."""
    jar_path = jar.bundled_jar()
    assert jar_path.exists()
    assert jar_path.name == "org.eclipse.dash.licenses-1.1.0.jar"


def test_build_cmdline_constructs_basic_command(monkeypatch: pytest.MonkeyPatch):
    """_build_cmdline constructs a valid Java command with required flags."""
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake.jar"))

    cmd = jar.build_cmdline(
        verbose=False,
        project=None,
        token=None,
        trigger_review=False,
        out_file=Path("/tmp/summary.txt"),
    )

    assert "java" in cmd
    assert "-Djava.net.useSystemProxies=true" in cmd
    assert "-jar" in cmd
    assert "/fake.jar" in cmd
    assert "-summary" in cmd
    assert "/tmp/summary.txt" in cmd
    assert "-" in cmd  # stdin indicator


def test_build_cmdline_includes_project_flag(monkeypatch: pytest.MonkeyPatch):
    """_build_cmdline includes project flag when provided."""
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake.jar"))

    cmd = jar.build_cmdline(
        verbose=False,
        project="my-project",
        token=None,
        trigger_review=False,
        out_file=Path("/tmp/summary.txt"),
    )

    assert "-project" in cmd
    assert "my-project" in cmd


def test_build_cmdline_includes_review_flags(monkeypatch: pytest.MonkeyPatch):
    """_build_cmdline includes review and token flags when provided."""
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake.jar"))

    cmd = jar.build_cmdline(
        verbose=False,
        project="my-project",
        token="secret-token",
        trigger_review=True,
        out_file=Path("/tmp/summary.txt"),
    )

    assert "-review" in cmd
    assert "-token" in cmd
    assert "secret-token" in cmd


def test_build_cmdline_includes_verbose_flag(monkeypatch: pytest.MonkeyPatch):
    """_build_cmdline includes verbose logging flag when enabled."""
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake.jar"))

    cmd = jar.build_cmdline(
        verbose=True,
        project=None,
        token=None,
        trigger_review=False,
        out_file=Path("/tmp/summary.txt"),
    )

    assert "-Dorg.slf4j.simpleLogger.defaultLogLevel=debug" in cmd


def test_build_cmdline_raises_error_when_review_without_token(
    monkeypatch: pytest.MonkeyPatch,
):
    """_build_cmdline raises ValueError if trigger_review without token."""
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake.jar"))

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        jar.build_cmdline(
            verbose=False,
            project="project",
            token=None,
            trigger_review=True,
            out_file=Path("/tmp/summary.txt"),
        )

    assert "Project and token must be specified" in str(exc_info.value)


def test_parse_jar_output_parses_dependencies_from_summary():
    """parse_jar_output correctly parses dependency rows from summary string."""
    summary_content = """pypi/pypi/-/colorama/0.4.6, BSD-2-Clause AND BSD-3-Clause, approved, clearlydefined
pypi/pypi/-/pytest/8.4.2, MIT, approved, #23205"""

    result = jar.parse_jar_output(summary=summary_content, stderr="")

    assert len(result.dependencies) == 2
    assert result.dependencies[0].package == "pypi/pypi/-/colorama/0.4.6"
    assert result.dependencies[0].license_raw == "BSD-2-Clause AND BSD-3-Clause"
    assert result.dependencies[0].license_pretty == "BSD-2-Clause AND BSD-3-Clause"
    assert result.dependencies[0].status == jar.ComplianceStatus.ALLOWED
    assert result.dependencies[1].package == "pypi/pypi/-/pytest/8.4.2"
    assert result.dependencies[1].license_raw == "MIT"
    assert result.dependencies[1].license_pretty == "MIT"


def test_parse_jar_output_extracts_issues_from_stderr():
    """parse_jar_output extracts lines containing http from stderr."""
    summary_content = "pypi/pypi/-/pytest/8.4.2, MIT, approved, #23205"

    stderr = """Some log line
http://example.com/issue/1234
Another log line
https://example.com/review/5678"""

    result = jar.parse_jar_output(summary=summary_content, stderr=stderr)

    assert len(result.issues) == 2
    assert any("http://example.com/issue/1234" in issue for issue in result.issues)
    assert any("https://example.com/review/5678" in issue for issue in result.issues)


def test_run_jar_exits_on_dry_run_before_calling_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """Dry run mode prints the command but doesn't execute it."""
    monkeypatch.setattr(jar, "require_java", lambda: None)

    subprocess_was_called = False

    def mock_subprocess_run(*args: Any, **kwargs: Any):
        nonlocal subprocess_was_called
        subprocess_was_called = True

    monkeypatch.setattr("dash_license_scan.jar.subprocess.run", mock_subprocess_run)

    with pytest.raises(SystemExit) as exc_info:
        jar.run_jar(
            dependencies="pypi/pypi/-/flask/3.0.0",
            dry_run=True,
        )

    assert exc_info.value.code == 0
    assert not subprocess_was_called

    output = capsys.readouterr().out
    assert "Would run command:" in output
    assert "With dependencies:" in output


def test_run_jar_produces_expected_output(
    monkeypatch: pytest.MonkeyPatch,
    fs: FakeFilesystem,
):
    """Integration test: run_jar executes subprocess and parses output correctly."""
    monkeypatch.setattr(jar, "require_java", lambda: None)
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake.jar"))

    # Mock subprocess.run to simulate execution with summary file creation
    def mock_subprocess_run(
        cmd: list[str], input: str, capture_output: bool, text: bool
    ):
        # Simulate the JAR creating a summary file
        summary_file_path = None
        for i, arg in enumerate(cmd):
            if arg == "-summary" and i + 1 < len(cmd):
                summary_file_path = cmd[i + 1]
                break

        if summary_file_path:
            summary_content = """pypi/pypi/-/colorama/0.4.6, BSD-2-Clause AND BSD-3-Clause, approved, clearlydefined
pypi/pypi/-/coverage/7.12.0, Apache-2.0 AND LicenseRef-scancode-iso-8879 AND (GPL-2.0-only AND MIT), restricted, #25641
pypi/pypi/-/pytest/8.4.2, MIT, approved, #23205"""
            Path(summary_file_path).write_text(summary_content)

        class MockResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return MockResult()

    monkeypatch.setattr("dash_license_scan.jar.subprocess.run", mock_subprocess_run)

    result = jar.run_jar(dependencies="pypi/pypi/-/flask/3.0.0")

    assert result
    assert isinstance(result, jar.JarResult)
    assert len(result.dependencies) == 3
    assert "pypi/pypi/-/colorama/0.4.6" in [row.package for row in result.dependencies]
    assert "BSD-2-Clause AND BSD-3-Clause" in [
        row.license_raw for row in result.dependencies
    ]
    assert "pypi/pypi/-/pytest/8.4.2" in [row.package for row in result.dependencies]

"""Unit tests for jar.py utility functions.

Tests focus on edge cases and error handling that provide value beyond e2e tests.
Command construction details are better verified through code review.
"""

import tempfile
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


def test_summary_file_or_tmp_file_uses_provided_path(tmp_path: Path):
    """When a path is provided, that exact path is used."""
    summary_file = tmp_path / "output" / "summary.txt"

    with jar.summary_file_or_tmp_file(summary_file) as path:
        assert path == summary_file
        assert path.parent.exists()


def test_summary_file_or_tmp_file_creates_temp_file_when_none_provided():
    """When no path is provided, a temporary file is created."""
    with jar.summary_file_or_tmp_file(None) as path:
        assert path.name.startswith("dash-license-scan-summary-")
        assert path.suffix == ".txt"
        assert path.parent == Path(tempfile.gettempdir())


def test_summary_file_or_tmp_file_cleans_up_temp_file_after_use():
    """Temporary files are deleted when the context exits."""
    temp_file_path = None

    with jar.summary_file_or_tmp_file(None) as path:
        temp_file_path = path
        path.write_text("test content")
        assert path.exists()

    assert temp_file_path is not None
    assert not temp_file_path.exists()


def test_summary_file_or_tmp_file_preserves_provided_file_after_use(tmp_path: Path):
    """User-provided paths are not deleted when context exits."""
    user_file = tmp_path / "keep-this.txt"

    with jar.summary_file_or_tmp_file(user_file) as path:
        path.write_text("important data")

    assert user_file.exists()
    assert user_file.read_text() == "important data"


def test_run_jar_exits_on_dry_run_before_calling_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    """Dry run mode prints the command but doesn't execute it."""
    monkeypatch.setattr(jar, "require_java", lambda: None)
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake.jar"))

    subprocess_was_called = False

    def mock_subprocess_run(*args: Any, **kwargs: Any):
        nonlocal subprocess_was_called
        subprocess_was_called = True

    monkeypatch.setattr("dash_license_scan.jar.subprocess.run", mock_subprocess_run)

    with pytest.raises(SystemExit) as exc_info:
        jar.run_jar(
            dependencies="pypi/pypi/-/flask/3.0.0",
            result_file=tmp_path / "out.txt",
            dry_run=True,
        )

    assert exc_info.value.code == 0
    assert not subprocess_was_called

    output = capsys.readouterr().out
    assert "Would run command:" in output
    assert "With dependencies:" in output
    assert "pypi/pypi/-/flask/3.0.0" in output

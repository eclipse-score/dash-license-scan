import shutil

import pytest

import dash_license_scan.jar as jar
from dash_license_scan.main import main


def _run_and_capture(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    return str(exc.value)


def test_java_message_ubuntu(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(jar, "is_ubuntu", lambda: True)

    msg = _run_and_capture(["--dry-run", "tests/data/pypi_1.txt"])
    assert "Java runtime not found" in msg
    assert "apt install openjdk-21-jre-headless" in msg


def test_java_message_other(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(jar, "is_ubuntu", lambda: False)

    msg = _run_and_capture(["--dry-run", "tests/data/pypi_1.txt"])
    assert "Java runtime not found" in msg
    assert "apt install" not in msg

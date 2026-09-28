from unittest.mock import patch

import pytest

from dash_license_scan import __version__
from dash_license_scan.main import main

from .common import dash_license_scan_main


def test_help(capsys):
    dash_license_scan_main(["--help"])

    captured = capsys.readouterr()
    combined: str = (captured.out or "") + (captured.err or "")
    assert "usage:" in combined


def test_version(capsys):
    main(["--version"])

    captured = capsys.readouterr()
    combined: str = (captured.out or "") + (captured.err or "")
    assert __version__ in combined


def test_invalid_argument(capsys):
    with pytest.raises(SystemExit):
        main(["--this_argument_does_not_exist"])


def test_dash_licenses_command_uses_stdin_and_jvm_options(tmp_path):
    lockfile = tmp_path / "requirements.txt"
    lockfile.write_text("pytest==9.0.0\n", encoding="utf-8")
    summary = tmp_path / "summary.txt"
    summary.write_text("summary\n", encoding="utf-8")

    with (
        patch("dash_license_scan.main.jar.require_java"),
        patch(
            "dash_license_scan.main.jar.get_jar", return_value=tmp_path / "licenses.jar"
        ),
        patch("dash_license_scan.main.subprocess.run") as run,
    ):
        run.return_value.returncode = 0
        main(["-v", "--summary", str(summary), str(lockfile)])

    run.assert_called_once_with(
        [
            "java",
            "-Dorg.slf4j.simpleLogger.defaultLogLevel=debug",
            "-jar",
            str(tmp_path / "licenses.jar"),
            "-summary",
            str(summary),
            "-",
        ],
        input="pypi/pypi/-/pytest/9.0.0",
        text=True,
    )

import pytest
from tests.common import safe_run_main

from dash_license_scan import __version__


def test_help_exits_with_usage(capsys: pytest.CaptureFixture[str]):
    assert safe_run_main(["--help"]) == 0

    out = capsys.readouterr().out
    assert "Wrapper around eclipse-dash/dash-licenses" in out


def test_version_exits_with_version(capsys: pytest.CaptureFixture[str]):
    assert safe_run_main(["--version"]) == 0

    out = capsys.readouterr().out
    assert __version__ in out


def test_invalid_argument_exits_error(capsys: pytest.CaptureFixture[str]):
    assert safe_run_main(["--unknown", "requirements.txt"]) == 2

    err = capsys.readouterr().err
    assert "unrecognized arguments" in err


def test_dry_run_and_review_are_mutually_exclusive(capsys: pytest.CaptureFixture[str]):
    """--dry-run and --review flags cannot be used together."""
    assert safe_run_main(["--dry-run", "--review", "requirements.txt"]) == 2

    err = capsys.readouterr().err
    assert "cannot be used together" in err.lower() or "mutually exclusive" in err.lower()

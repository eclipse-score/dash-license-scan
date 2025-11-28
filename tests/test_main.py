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

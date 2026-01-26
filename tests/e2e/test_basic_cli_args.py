import pytest
from tests.e2e.conftest import ProductTestKit

from dash_license_scan import __version__


def test_help_exits_with_usage(product_test_kit: ProductTestKit):
    assert product_test_kit.run(["--help"]) == 0

    assert "Wrapper around eclipse-dash/dash-licenses" in product_test_kit.stdout


def test_version_exits_with_version(product_test_kit: ProductTestKit):
    assert product_test_kit.run(["--version"]) == 0

    assert __version__ in product_test_kit.stdout


def test_invalid_argument_exits_error(product_test_kit: ProductTestKit):
    assert product_test_kit.run(["--unknown", "requirements.txt"]) == 2

    assert "unrecognized arguments" in product_test_kit.stderr


def test_dry_run_and_review_are_mutually_exclusive(product_test_kit: ProductTestKit):
    """--dry-run and --trigger-review flags cannot be used together."""
    assert (
        product_test_kit.run(["--dry-run", "--trigger-review", "requirements.txt"]) == 2
    )

    err = product_test_kit.stderr
    assert (
        "cannot be used together" in err.lower() or "mutually exclusive" in err.lower()
    )

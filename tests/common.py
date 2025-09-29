"""Test helpers for dash_license_scan tests.

Keep imports lazy so importing this module at collection time doesn't
fail when the package under test isn't on sys.path.
"""


def dash_license_scan_main(args):
    # Import inside the function to avoid ModuleNotFoundError during
    # pytest collection when tests are imported as a package.
    from dash_license_scan.main import main

    exit_code = None
    try:
        exit_code = main(args)
    except SystemExit as e:
        if isinstance(e.code, int):
            exit_code = e.code
        else:
            raise AssertionError(f"Unexpected SystemExit: {e.code}") from e

    if exit_code:
        raise AssertionError(
            f"dash_license_scan.main() returned exit code {exit_code}"
        )

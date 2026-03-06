from __future__ import annotations

from dash_license_scan.main import main as real_main


def safe_run_main(argv: list[str] | None = None) -> int:
    """Catch SystemExit and convert error code to normal return."""

    try:
        return real_main(argv)
    except SystemExit as e:
        if isinstance(e.code, int):
            return e.code
        else:
            raise

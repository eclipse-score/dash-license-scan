"""Focused unit tests for main.py functions.

Most CLI behavior is covered by e2e tests. These unit tests focus on
the parse_all_lockfiles function's logic for combining multiple file formats.
"""

from pathlib import Path

from dash_license_scan import main


def test_parse_all_lockfiles_combines_results_from_multiple_files(tmp_path: Path) -> None:
    """When multiple lockfiles are provided, all dependencies are collected."""
    requirements_txt = tmp_path / "requirements.txt"
    requirements_txt.write_text("requests==2.32.0")

    cargo_lock = tmp_path / "Cargo.lock"
    cargo_lock.write_text("""
version = 4

[[package]]
name = "serde"
version = "1.0.203"
source = "registry+https://github.com/rust-lang/crates.io-index"
""")

    all_dependencies = main.parse_all_lockfiles([requirements_txt, cargo_lock])

    assert len(all_dependencies) == 2
    assert "pypi/pypi/-/requests/2.32.0" in all_dependencies
    assert "crate/cratesio/-/serde/1.0.203" in all_dependencies


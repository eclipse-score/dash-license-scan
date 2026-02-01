"""Shared pytest fixtures for e2e tests."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyfakefs.fake_filesystem_unittest import Patcher

import dash_license_scan.jar as jar

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.monkeypatch import MonkeyPatch
    from pyfakefs.fake_filesystem import FakeFilesystem


@dataclass
class ProductTestKit:
    # Wrapped & centralized test utilities (e2e harness)
    fs: FakeFilesystem
    capsys: pytest.CaptureFixture[str]
    monkeypatch: MonkeyPatch

    # Outputs of the fake jar subprocess.run invocations
    jar_cmd: list[str] | None = None
    jar_input: str | None = None

    def set_fake_jar_response(
        self, issues: int, summary_text: str, stderr: str = "log-line"
    ) -> None:
        """Stub subprocess.run used by jar.run_jar and record invocation."""

        def _run(cmd: list[str], *, input: str, capture_output: bool, text: bool):  # type: ignore[override]
            self.jar_cmd = cmd
            self.jar_input = input
            summary_arg_index = cmd.index("-summary") + 1
            summary_path = Path(cmd[summary_arg_index])
            summary_path.write_text(summary_text)
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=issues,
                stdout="",
                stderr=stderr,
            )

        self.monkeypatch.setattr(jar, "subprocess", type("_S", (), {"run": _run}))

    def fake_requirements_file(
        self, lines: list[str], path: str = "/work/requirements.txt"
    ) -> Path:
        self.fs.create_file(path, contents="\n".join(lines))
        return Path(path)

    def set_env(self, project: str = "proj", token: str = "tok") -> None:
        self.monkeypatch.setenv("ECLIPSE_PROJECT", project)
        self.monkeypatch.setenv("DASH_TOKEN", token)

    def run(self, argv: list[str]) -> int:
        """Invoke CLI main, returning its exit code even when SystemExit is raised."""

        # Reapply in case tests import main before the fixture.
        self.monkeypatch.setattr(
            "dash_license_scan.main.load_dotenv", lambda *_, **__: None, raising=False
        )
        self.monkeypatch.setattr(
            "dotenv.main.load_dotenv", lambda *_, **__: None, raising=False
        )
        self.monkeypatch.setattr(
            "dotenv.main.find_dotenv", lambda *_, **__: "", raising=False
        )

        from dash_license_scan.main import main

        try:
            return main(argv)
        except SystemExit as exc:
            return exc.code if isinstance(exc.code, int) else 1

    @property
    def stdout(self) -> str:
        return self.capsys.readouterr().out

    @property
    def stderr(self) -> str:
        return self.capsys.readouterr().err


@pytest.fixture
def product_test_kit(
    monkeypatch: MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Generator[ProductTestKit, None, None]:
    """End-to-end harness with fake jar + fake FS for CLI tests."""

    git_root = Path(__file__).parent.parent.parent
    resources_dir = git_root / "src" / "dash_license_scan" / "resources"
    assert resources_dir.exists()

    patcher = Patcher(additional_skip_names=["importlib", "importlib.resources"])
    patcher.setUp()
    assert patcher.fs is not None
    patcher.fs.add_real_directory(str(resources_dir), lazy_read=True, read_only=True)

    monkeypatch.setattr(jar, "require_java", lambda: None)
    monkeypatch.setattr(jar, "bundled_jar", lambda: Path("/fake/jar.jar"))
    monkeypatch.setattr("dash_license_scan.cli.load_dotenv", lambda *_, **__: None)

    kit = ProductTestKit(fs=patcher.fs, capsys=capsys, monkeypatch=monkeypatch)
    try:
        yield kit
    finally:
        patcher.tearDown()

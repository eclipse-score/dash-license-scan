"""Java integration wrapper for the eclipse-dash/dash-licenses JAR.

This module centralizes:
- locating the embedded JAR
- validating Java availability with helpful platform guidance
- constructing and executing the command to run the scanner
- handling stdout/stderr, exit codes, and temporary summary files
"""

import importlib.resources
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager, suppress
from logging import getLogger
from pathlib import Path

log = getLogger(__name__)


def is_ubuntu() -> bool:
    try:
        return "ID=ubuntu" in Path("/etc/os-release").read_text()
    except Exception:
        return False


def require_java() -> None:
    if shutil.which("java"):
        return

    msg = [
        "Error: Java runtime not found on PATH.",
        "",
        "Install a Java 21+ runtime and ensure `java` is available.",
    ]

    if is_ubuntu():
        msg += [
            "",
            "Instructions: `sudo apt update && sudo apt install openjdk-21-jre-headless`",
        ]

    sys.exit("\n".join(msg))


def _get_cache_dir() -> Path:
    cache_dir = (
        Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "dash-license-scan"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def bundled_jar() -> Path:
    """Return a filesystem path to the bundled dash-licenses JAR."""

    res = (
        importlib.resources.files("dash_license_scan.resources")
        / "org.eclipse.dash.licenses-1.1.0.jar"
    )
    with importlib.resources.as_file(res) as p:
        return p


@contextmanager
def summary_file_or_tmp_file(summary_file: Path | None):
    """Context manager yielding a Path to a summary file.

    If summary_file is provided, it is used. Otherwise, a temporary file is created
    and deleted on exit.
    """

    if summary_file:
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        yield summary_file

    else:
        # Do not use context manager, as we need to fully close the file, so the external
        # application (Java) can open it for exclusive writing.
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
            prefix="dash-license-scan-summary-", suffix=".txt", delete=False
        )
        tmp_file = Path(tmp.name)
        tmp.close()
        try:
            yield tmp_file
        finally:
            with suppress(OSError):
                tmp_file.unlink()


def run_jar(
    *,
    dependencies: str,
    verbose: bool = False,
    result_file: Path | None = None,
    dry_run: bool = False,
    project: str | None = None,
    token_for_review: str | None = None,
) -> tuple[int, str]:
    """Run the dash-licenses JAR with the given dependencies.

    Returns a tuple of (#issues found, summary text).

    Note: presence of a token indicates review mode!
    """

    require_java()  # ensure Java is available even for dry-run

    jar_path = bundled_jar()

    with summary_file_or_tmp_file(result_file) as out:
        cmd = ["java", "-Djava.net.useSystemProxies=true"]
        if verbose:
            # According to documentation this is verbose mode, but it does not seem to have any effect
            cmd.append("-Dorg.slf4j.simpleLogger.defaultLogLevel=debug")
        cmd.extend(["-jar", str(jar_path)])
        cmd.extend(["-summary", str(out)])
        if project:
            cmd.extend(["-project", project])
        if token_for_review:
            cmd.append("-review")
            cmd.extend(["-token", token_for_review])

        cmd.extend(["-"])  # Read dependencies from stdin
        log.debug(f"Running command: {' '.join(cmd)}")

        if dry_run:
            print(f"Would run command: {' '.join(cmd)}")
            print("With dependencies:")
            print("\n".join(dependencies.split("\n")))
            raise SystemExit(0)

        result = subprocess.run(
            cmd,
            input=dependencies,
            capture_output=True,
            text=True,
        )
        # 0 is all ok
        # [1,126] is the number of dependencies with issues
        if result.returncode < 0 or result.returncode > 126:
            log.error(f"dash-licenses failed with exit code {result.returncode}")
            log.error(f"stdout: {result.stdout}")
            log.error(f"stderr: {result.stderr}")
            raise SystemExit(result.returncode)

        # stdout is always empty
        if result.stdout:
            log.warning(f"Unexpected stdout: {result.stdout}")

        # stderr has logs, print only in verbose mode
        for line in result.stderr.splitlines():
            log.debug(f"dash-licenses: {line}")

        return result.returncode, out.read_text()

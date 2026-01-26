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
from dataclasses import dataclass
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


@dataclass
class JarResult:
    summarize: str
    log: str
    issues: list[str]


def run_jar(
    *,
    dependencies: str,
    verbose: bool = False,
    dry_run: bool = False,
    project: str | None = None,
    token_for_review: str | None = None,
) -> JarResult:
    """Run the dash-licenses JAR with the given dependencies.

    Note: presence of a token indicates review mode!
    """

    jar_path = bundled_jar()

    with tempfile.TemporaryDirectory(prefix="dash-licenses-") as tmpdir:
        out_file = Path(tmpdir) / "summary.txt"

        cmd = ["java", "-Djava.net.useSystemProxies=true"]
        if verbose:
            # According to documentation this is verbose mode, but it does not seem to have any effect
            cmd.append("-Dorg.slf4j.simpleLogger.defaultLogLevel=debug")
        cmd.extend(["-jar", str(jar_path)])
        cmd.extend(["-summary", str(out_file)])
        if project:
            cmd.extend(["-project", project])
        if token_for_review:
            if not project:
                raise ValueError("Project must be specified when using review mode.")

            cmd.append("-review")
            cmd.extend(["-token", token_for_review])

        cmd.extend(["-"])  # Read dependencies from stdin

        masked_cmd = [str(c) if c != token_for_review else "<REDACTED>" for c in cmd]

        if dry_run:
            print(f"Would run command: {' '.join(masked_cmd)}")
            print("With dependencies:")
            print("\n".join(dependencies.split("\n")))
            raise SystemExit(0)

        require_java()  # ensure Java is available

        log.debug(f"Running command: {' '.join(masked_cmd)}")

        result = subprocess.run(
            cmd,
            input=dependencies,
            capture_output=True,
            text=True,
        )
        # 0 is all ok
        # [1,126] is the number of dependencies with issues
        if not (result.returncode >= 0 and result.returncode <= 126):
            log.error(f"dash-licenses failed with exit code {result.returncode}")
            log.error(f"stdout: {result.stdout}")
            log.error(f"stderr: {result.stderr}")
            raise SystemExit(2)

        # stdout is always empty
        if result.stdout:
            log.warning(f"Unexpected stdout: {result.stdout}")

        result = JarResult(
            summarize=out_file.read_text(),
            log=result.stderr,
            issues=[],
        )
        for line in result.log.splitlines():
            if "http" in line:
                result.issues.append(line)
            log.debug(f"dash-licenses: {line}")

        return result

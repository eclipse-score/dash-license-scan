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
class Dependency:
    package: str
    license: str
    status: str
    note: str


@dataclass
class JarResult:
    summarize: str
    log: str
    issues: list[str]  # experimental
    dependencies: list[Dependency]

    def set_rows_from_summary(self, summary: str) -> None:
        rows: list[Dependency] = []
        for line in summary.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 4:
                continue
            row = Dependency(
                package=parts[0],
                license=parts[1],
                status=parts[2],
                note=parts[3],
            )
            log.debug(f"Parsed summary row {line} => {row}")
            rows.append(row)
        self.dependencies = rows


def build_cmdline(
    *,
    verbose: bool,
    project: str | None,
    token: str | None,
    out_file: Path,
    trigger_review: bool,
) -> list[str]:
    """Build the command line arguments for the dash-licenses JAR."""

    if trigger_review and (not project or not token):
        raise ValueError("Project and token must be specified when using review mode.")

    cmd = ["java", "-Djava.net.useSystemProxies=true"]
    if verbose:
        cmd.append("-Dorg.slf4j.simpleLogger.defaultLogLevel=debug")
    cmd.extend(["-jar", str(bundled_jar())])
    cmd.extend(["-summary", str(out_file)])
    if project:
        cmd.extend(["-project", project])
    if token:
        cmd.extend(["-token", token])
    if trigger_review:
        cmd.append("-review")

    cmd.extend(["-"])  # Read dependencies from stdin
    return cmd


def run_cmdline(cmd: list[str], dependencies: str) -> subprocess.CompletedProcess[str]:
    """Execute the dash-licenses JAR command.

    Args:
        cmd: Command line arguments to execute
        dependencies: Dependencies string to pass via stdin

    Returns:
        CompletedProcess with returncode, stdout, and stderr

    Raises:
        SystemExit: If the command fails with an invalid exit code
    """
    require_java()  # ensure Java is available

    result = subprocess.run(
        cmd,
        input=dependencies,
        capture_output=True,
        text=True,
    )

    # 0 is all ok
    # [1,126] is the number of issues created in this run
    # We don't care whether issues preexisted or were just created now.
    if result.returncode < 0 or result.returncode > 126:
        log.error(f"dash-licenses failed with exit code {result.returncode}")
        log.error(f"stdout: {result.stdout}")
        log.error(f"stderr: {result.stderr}")
        raise SystemExit(2)

    return result


def parse_jar_output(summary: str, stderr: str) -> JarResult:
    """Parse the output from the dash-licenses JAR execution.

    Args:
        summary: The summary output from the JAR execution
        stderr: The stderr output from the JAR execution

    Returns:
        JarResult with parsed dependencies and issues
    """
    result = JarResult(
        summarize=summary,
        log=stderr,
        issues=[],
        dependencies=[],
    )

    for line in result.log.splitlines():
        if "http" in line:
            result.issues.append(line)
        log.debug(f"dash-licenses: {line}")

    result.set_rows_from_summary(result.summarize)

    return result


def run_jar(
    *,
    dependencies: str,
    verbose: bool = False,
    dry_run: bool = False,
    project: str | None = None,
    token: str | None = None,
    trigger_review: bool = False,
) -> JarResult:
    """Run the dash-licenses JAR with the given dependencies.

    Note: presence of a token indicates review mode!
    """
    with tempfile.TemporaryDirectory(prefix="dash-licenses-") as tmpdir:
        out_file = Path(tmpdir) / "summary.txt"

        cmd = build_cmdline(
            verbose=verbose,
            project=project,
            token=token,
            out_file=out_file,
            trigger_review=trigger_review,
        )
        masked_cmd = [str(c) if c != token else "<REDACTED>" for c in cmd]

        if dry_run:
            print(f"Would run command: {' '.join(masked_cmd)}")
            print("With dependencies:")
            print("\n".join(dependencies.split("\n")))
            raise SystemExit(0)

        else:  # noqa: RET506

            log.debug(f"Running command: {' '.join(masked_cmd)}")

            result = run_cmdline(cmd, dependencies)

            if result.stdout:
                log.warning(f"Unexpected stdout: {result.stdout}")

            return parse_jar_output(out_file.read_text(), result.stderr)

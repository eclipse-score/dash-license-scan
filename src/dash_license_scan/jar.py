import importlib.resources
import os
import shutil
import sys
from logging import getLogger
from pathlib import Path

log = getLogger(__name__)


def is_ubuntu() -> bool:
    try:
        return "ID=ubuntu" in Path("/etc/os-release").read_text()
    except Exception:
        return False


def require_java():
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
        Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
        / "dash-license-scan"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_jar() -> Path:
    res = (
        importlib.resources.files("dash_license_scan.resources")
        / "org.eclipse.dash.licenses-1.1.0.jar"
    )
    with importlib.resources.as_file(res) as p:
        return p

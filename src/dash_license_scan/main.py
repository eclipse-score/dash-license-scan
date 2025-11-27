from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

from dash_license_scan import jar
from dash_license_scan.cli import parse_args
from dash_license_scan.parsers import parse

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------------------------------------


def real_main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.verbose:
        log.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)

    log.debug("Starting dash_license_scan.main(%s)", argv)
    log.debug("Parsed args: %s", args)

    jar.require_java()  # ensure Java is available even for dry-run
    jar_path = jar.get_jar()
    log.debug(f"Using dash-licenses JAR at {jar_path}")

    deps: list[str] = []

    for file in args.lockfiles:
        log.debug(f"Parsing lockfile: {file}")
        parsed = parse(file)
        log.debug(f"Parsed dependencies from {file}: {parsed}")

        deps.extend(parsed)

    if args.dry_run:
        print("Detected dependencies:")
        print("\n".join(deps))
        return

    # TODO: should we cache the results? Forever? For some minutes? Configurable?
    log.info(f"Running dash-licenses with {len(deps)} dependencies")

    # Determine summary output path: user-provided or ephemeral temp file.
    if args.summary is not None:
        summary_path = Path(args.summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file_path: Path | None = None
    else:
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
            prefix="dash-license-scan-summary-", suffix=".txt", delete=False
        )
        summary_path = Path(tmp.name)
        tmp.close()  # explicit close; not using context manager so Java can reopen
        temp_file_path = summary_path

    try:
        cmd = [
            "java",
            "-jar",
            str(jar_path),
            "-summary",
            str(summary_path),
        ]
        if args.verbose:
            # According to documentation, but does not seem to have any effect:
            cmd.append("-Dorg.slf4j.simpleLogger.defaultLogLevel=debug")
        cmd.append("-")  # read dependencies from stdin
        log.debug(f"Command: {' '.join(cmd)}")
        deps_input = "\n".join(deps)
        result = subprocess.run(cmd, input=deps_input, text=True)

        print("")
        print("Dash Licenses Summary Output:")
        print(summary_path.read_text(encoding="utf-8"), end="")
        sys.exit(result.returncode)
    finally:
        if temp_file_path:
            with suppress(OSError):
                temp_file_path.unlink()


def main(argv: list[str] | None = None) -> None:
    # Catch SystemExit and convert error code 0 to normal return.
    try:
        real_main(argv)
    except SystemExit as e:
        if e.code == 0:
            return  # normal exit
        else:
            raise


if __name__ == "__main__":
    main()

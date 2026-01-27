# dash-license-scan

[![PyPI](https://img.shields.io/pypi/v/dash-license-scan.svg)](https://pypi.org/project/dash-license-scan/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A thin Python CLI wrapper for [eclipse-dash/dash-licenses](https://github.com/eclipse-dash/dash-licenses).  
It makes the official JAR easier to use via modern Python workflows (`pipx`, `uvx`) and adds helpers for lockfile conversion.

---

## State

Proof of Concept. Do not use in production environments.

---

## Features

- **Simple to use**: Focus on usability
- **Easy installation**: Run with [`pipx`](https://pypa.github.io/pipx/) or [`uvx`](https://docs.astral.sh/uv/concepts/tools/) - no complex setup required
- **Self-contained**: Self-contained tool with `dash-licenses` JAR included for simplified version management.
- **Lockfile support**: Supports scanning common lockfile formats:
  - `requirements.txt` (Python with pip-tools)
  - `uv.lock` (Python with uv)
  - `Cargo.lock` (Rust)

### Planned Features

- Auto-detect lockfiles in current directory
- Support more lock file formats, e.g. bazel.
- Detect GitHub pull request invocation and print diff
- Compare against additional license limitations (e.g., allowed licenses list)
- Auto-detect Eclipse project environment configuration
- Trigger Eclipse IP-Team review for unknown dependencies

---

## Installation

**System Requirements:**
- `uvx` or `pipx` installed
- Java >= 11 (e.g., `openjdk-21-jre-headless`)

That's it!

## Usage

The tool automatically detects the lockfile type based on filename and extension:

```bash
# Scan a Python requirements file
uvx dash-license-scan requirements.txt

# Scan a uv.lock file
uvx dash-license-scan uv.lock

# Scan a Rust Cargo lockfile
uvx dash-license-scan Cargo.lock

# Scan multiple lockfiles at once
uvx dash-license-scan requirements.txt uv.lock Cargo.lock

# Dry-run to see detected dependencies without invoking dash-licenses
uvx dash-license-scan --dry-run uv.lock
```


For verbose logging:
```bash
uvx dash-license-scan -v requirements.txt
```

### Triggering a Review of Unknown Licenses

Use `--trigger-review` flag to trigger an Eclipse IP-Team review for unknown licenses. Requires two environment variables:

1. **`DASH_TOKEN` or `ECLIPSE_GITLAB_API_TOKEN`** — Generate from https://gitlab.eclipse.org/-/user_settings/personal_access_tokens (scope: `api`)
2. **`ECLIPSE_PROJECT`** — Your Eclipse project identifier (e.g., `automotive.score`)

**Option A: Set as environment variables**
```bash
export DASH_TOKEN=<your_token>
export ECLIPSE_PROJECT=automotive.score
uvx dash-license-scan uv.lock --trigger-review
```

**Option B: Create a `.env` file**
```bash
DASH_TOKEN=<your_token>
ECLIPSE_PROJECT=automotive.score
```
Then run:
```bash
uvx dash-license-scan uv.lock --trigger-review
```

---

## Usage in Automations

**This is planned functionality. Workflow does not exist yet.**

Expected behavior by users:

PR -> scan -> cannot parse dependencies --> 🔴
PR -> scan -> all dependencies are approved --> 🟢 + PR comment with a list of dependencies and their licenses.
PR -> scan -> some dependencies are unknown --> 🟢 + PR comment with a list of dependencies and their licenses & status.
PR -> scan -> some dependencies in review --> 🟢 + PR comment with a list of dependencies and their licenses & status. Links to the review tickets.
PR -> scan -> some dependencies rejected --> 🔴 + PR comment with a list of dependencies and their licenses & status. Links to the tickets.

Implementation:

- GitHub Action that triggers on PR, triggers `dash-license-scan` and uploads the results as a PR comment.
- GitHub Action that triggers on new comments with `@dash-license-scan recheck` to re-check the status of dependencies in review via `dash-license-scan`.
- GitHub Action that triggers on new comments with `@dash-license-scan trigger-review` to create review tickets for unknown dependencies via `dash-license-scan --trigger-review`.


## Why a Python wrapper?

Why not extend the Java code directly? Here are the reasons:

- **Simplicity**: One-line usability with `uvx`/`pipx` 
- **Ecosystem fit**: Most projects already use pip/uv for Python dependencies, making versioning and offline installs seamless
- **Modern tooling**: Leverages modern Python packaging and execution workflows

This tool may not be for everyone, but if it helps S-CORE, it might help you too.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setting up a development environment, running tests, and contributing code.

## License

This wrapper is licensed under Apache-2.0 (unlike dash-licenses which uses EPL) to align with S-CORE's licensing standards. Licensing under EPL can certainly be discussed if there is interest. Note that this might become significantly more complex once there is more authors etc!!

# dash-license-scan

[![PyPI](https://img.shields.io/pypi/v/dash-license-scan.svg)](https://pypi.org/project/dash-license-scan/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

______________________________________________________________________

Analyze your project's dependencies for license compliance using the Eclipse Dash License Scanner (`dash-licenses`) with ease.

:warning: Proof of Concept. Do not use in production environments.

______________________________________________________________________

## Features

A thin Python CLI wrapper for [eclipse-dash/dash-licenses](https://github.com/eclipse-dash/dash-licenses).
It makes the official JAR easier to use via modern Python workflows (`pipx`, `uvx`) and adds helpers for lockfile conversion.

- **Simple to use**: Focus on usability
- **Easy installation**: Run with [`pipx`](https://pypa.github.io/pipx/) or [`uvx`](https://docs.astral.sh/uv/concepts/tools/) - no setup required
- **Self-contained**: Self-contained tool with `dash-licenses` JAR included for simplified version management.
- **Lockfile support**: Supports scanning common lockfile formats:
  - `requirements.txt` (Python with pip-tools)
  - `uv.lock` (Python with uv)
  - `Cargo.lock` (Rust)

______________________________________________________________________

## GitHub Actions Usage

Add a step, e.g. to your on-PR workflow:

```
      - uses: eclipse-score/dash-license-scan@dev
        with:
          token: ${{ secrets.DASH_API_TOKEN }}
          eclipse_project: ${{ vars.ECLIPSE_PROJECT }}
          trigger_review: false
```

And it will print analysis results as a comment on the PR.

______________________________________________________________________

## Local Installation

**System Requirements:**

- `uvx` or `pipx` installed
- Java >= 11 (e.g., `openjdk-21-jre-headless`)

That's it!

## Local Usage

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

### Run compliance evaluation for identified licenses

Use `--comply-with` flag to trigger compliance evaluation against a specific policy. Currently supported policies are:

- `ASF` - Apache Software Foundation's (ASF) 3rd Party License Policy.
- `EF` - Eclipse Foundation - Third Party Content Licenses.

Usage:

```bash
uvx dash-license-scan uv.lock --comply-with <policy-name>

uvx dash-license-scan uv.lock --comply-with ASF
uvx dash-license-scan uv.lock --comply-with EF
```

______________________________________________________________________

## Why a Python wrapper?

Why not extend the Java code directly? Here are the reasons:

- **Simplicity**: One-line usability with `uvx`/`pipx`
- **Ecosystem fit**: Most projects already use pip/uv for Python dependencies, making versioning and offline installs seamless

*This tool may not be for everyone, but if it helps S-CORE, it might help you too.*

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setting up a development environment, running tests, and contributing code.

## License

This repo is prepared under Apache-2.0 (unlike dash-licenses which uses EPL) to align with S-CORE's licensing standards. However EPL can certainly be discussed if there is interest! Note that this might become significantly more complex once there is more authors!!

# Contributing to dash-license-scan

Thank you for your interest in contributing! This document provides guidelines and instructions for setting up your development environment.

## Code of Conduct

This project follows the [Eclipse Code of Conduct](https://www.eclipse.org/org/documents/Community_Code_of_Conduct.php).

## Getting Started

### Prerequisites

- Python 3.10 or later
- `uv` installed ([Installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- Java >= 11 (for running the dash-licenses JAR)

### Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/eclipse-dash/dash-license-scan.git
   cd dash-license-scan
   ```

1. **Create a virtual environment and install dependencies:**

   ```bash
   uv sync --extra dev
   ```

   This command:

   - Creates a virtual environment (if not already present)
   - Installs all dependencies and optional dev dependencies from `pyproject.toml`
   - Installs the package in editable mode

1. **Activate the virtual environment:**

   ```bash
   source .venv/bin/activate
   ```

1. **Install pre-commit hooks:** *(optional but recommended)*

   ```bash
   pre-commit install
   ```

   This will automatically run code formatting, linting, and type checking before each commit.

### Code Quality Checks

We use pre-commit hooks to maintain code quality. The hooks automatically run:

- **ruff format** - Code formatting
- **ruff check** - Linting with automatic fixes
- **basedpyright** - Type checking

**Run hooks manually on all files:**

```bash
pre-commit run --all-files
```

**Run hooks on staged files only:**

```bash
pre-commit run
```

**Skip hooks for a commit**

*e.g. when you commit during your TDD cycle, you may want to skip pre-commit for every commit*

```bash
git commit --no-verify
```

### Running Tests

Run the test suite:

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/unit/test_main.py

# Run tests with coverage
uv run pytest --cov=src/dash_license_scan --cov-report=term-missing
```

### Running the Application

To run the application, use the following command:

```bash
uv run dash-license-scan
```

## Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Include a clear description of your changes
- Contrary to other projects, that claim tests but do not test, dash-license-scan requires tests for new features and bug fixes
- Ensure all tests pass locally before submitting
- Ensure pre-commit hooks pass (run `pre-commit run --all-files` to check)
- Reference any related issues

## License

By contributing to this project, you agree that your contributions will be licensed under the defined License (see LICENSE file).

## Additional Resources

- [dash-licenses Repository](https://github.com/eclipse-dash/dash-licenses)
- [Eclipse Development Process](https://www.eclipse.org/projects/dev_process/)

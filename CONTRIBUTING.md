# Contributing to WasmDock

Thank you for your interest in contributing to WasmDock. This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10+
- Docker Desktop with [WASM support enabled](https://docs.docker.com/desktop/wasm/)
- Rust toolchain (for testing template builds)

### Getting Started

```bash
git clone https://github.com/hariharanragothaman/wasmdock.git
cd wasmdock
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Pre-commit hooks

Install the git hooks so linting, formatting, and type checks run automatically
before each commit (mirrors CI):

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # optional: run against the whole tree
```

### Running Tests

```bash
pytest -v
pytest --cov=wasmdock --cov-report=term-missing
```

### Linting and Formatting

WasmDock uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [mypy](https://mypy-lang.org/) for type checking.

```bash
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

### Using Docker Compose

```bash
docker compose run test    # run tests
docker compose run lint    # run linters
docker compose up dev      # interactive development shell
```

## How to Contribute

### Reporting Bugs

Use the [Bug Report](https://github.com/hariharanragothaman/wasmdock/issues/new?template=bug_report.md) issue template. Include:

- WasmDock version, Python version, Docker version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error output

### Suggesting Features

Use the [Feature Request](https://github.com/hariharanragothaman/wasmdock/issues/new?template=feature_request.md) issue template.

### Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`: `git checkout -b feature/my-feature`
3. Make your changes with clear, descriptive commits
4. Ensure all tests pass and linters are clean
5. Open a pull request against `main`

### Pull Request Guidelines

- Keep PRs focused -- one feature or fix per PR
- Add or update tests for any changed behavior
- Update documentation if applicable
- Follow the existing code style (enforced by Ruff)
- Include type annotations for all public functions

### Adding a New Template

1. Create a new directory under `src/wasmdock/templates/`
2. Add `Dockerfile.j2`, `Cargo.toml.j2`, and source file templates
3. Register the template in `src/wasmdock/templates/__init__.py`
4. Add tests in `tests/test_scaffolder.py`
5. Document the template in the README

### Adding a New Runtime

1. Add the runtime to the `WasmRuntime` enum in `src/wasmdock/models.py`
2. Add the containerd runtime string to `_CONTAINERD_RUNTIMES`
3. Add display name and description
4. Update tests and documentation

## Code Style

- Use `from __future__ import annotations` for postponed evaluation
- Prefer dataclasses for plain data containers
- Use `Path` objects over string paths internally
- Keep functions focused and under 50 lines where practical
- Type-annotate all public functions and methods

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

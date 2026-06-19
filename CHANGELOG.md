# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `wasmdock doctor` command to diagnose the Docker WASM environment.
- `wasmdock stop`, `wasmdock logs`, `wasmdock pull` commands.
- `wasmdock ps` and `wasmdock clean` commands.
- `python -m wasmdock` entry point and PEP 561 `py.typed` marker.
- Runnable `examples/hello-wasm` project with a `Makefile`.
- Release workflow (PyPI Trusted Publishing), CodeQL scanning, Dependabot,
  and a pre-commit configuration.
- Documentation site (mkdocs-material), `SECURITY.md`, `CODEOWNERS`,
  and a pull request template.

### Changed
- `wasmdock run` is now idempotent (replaces an existing project container).

### Fixed
- `wasmdock build` now runs through the Docker CLI (BuildKit) instead of the
  legacy docker-py build API, which did not populate `$BUILDPLATFORM` and made
  every multi-stage template build fail. Verified end-to-end against Docker
  Desktop with WASM enabled.
- Bumped the Rust template base image `1.79` → `1.86` (the `spin-sdk`/`url`
  dependency trees now require `edition2024` and rustc ≥ 1.86).
- Added the missing `anyhow` dependency to the Spin and edge-function templates.
- Fixed the TinyGo template to write its build output to the work dir (the
  TinyGo image runs as a non-root user and cannot write to `/`).
- Packaging metadata (invalid trove classifier; wheel template duplication).
- Linting, formatting, typing, and a flaky build-time test so CI is green.

## [0.1.0] - Initial scaffold

### Added
- Initial WasmDock toolkit: `init`, `build`, `run`, `bench`, `push`,
  `templates`, `runtimes`, four project templates, and four runtimes.

[Unreleased]: https://github.com/hariharanragothaman/wasmdock/commits/main

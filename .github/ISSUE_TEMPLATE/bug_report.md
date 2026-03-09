---
name: Bug Report
about: Report a bug to help improve WasmDock
title: "[BUG] "
labels: bug
assignees: ''
---

## Description

A clear and concise description of the bug.

## Steps to Reproduce

1. Run `wasmdock init my-app --runtime wasmtime`
2. Run `wasmdock build`
3. ...

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened. Include full error output if applicable.

## Environment

- **WasmDock version**: `wasmdock --version`
- **Python version**: `python --version`
- **Docker version**: `docker --version`
- **Docker Desktop WASM support**: enabled / disabled
- **OS**: macOS / Linux / Windows (WSL2)

## Docker Info

```
Paste output of: docker info | grep -A5 -i wasm
```

## Additional Context

Add any other context about the problem here (logs, screenshots, config files).

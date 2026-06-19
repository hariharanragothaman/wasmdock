# WasmDock Documentation

## Overview

WasmDock is a Docker-native WASM development toolkit that lets you scaffold, build, run, and benchmark WebAssembly containers using Docker's native WASM runtime support.

## Quick Start

### Installation

```bash
pip install wasmdock
```

### Create Your First WASM Project

```bash
wasmdock doctor    # verify Docker WASM support is enabled
wasmdock init my-service --runtime wasmtime --template http-server-wasmtime
cd my-service
wasmdock build
wasmdock run
```

A ready-to-build version of this project lives in
[`examples/hello-wasm`](https://github.com/hariharanragothaman/wasmdock/tree/main/examples/hello-wasm).

## Core Concepts

### WASM Containers

Docker Desktop 4.15+ includes built-in support for running WebAssembly workloads alongside traditional Linux containers. Instead of packaging a full OS and userspace, a WASM container holds a single `.wasm` binary executed by a lightweight runtime shim (Wasmtime, WasmEdge, or Spin).

Key advantages over traditional Linux containers:

| Metric      | WASM Container | Linux Container |
|-------------|---------------|-----------------|
| Cold start  | ~1 ms         | ~300+ ms        |
| Image size  | ~2 MB         | ~50-200 MB      |
| Memory      | ~5 MB         | ~30-100 MB      |
| Sandboxing  | Capability-based | Namespace/cgroup |

### Runtimes

WasmDock supports four container runtimes:

- **Wasmtime** -- Bytecode Alliance reference implementation with broad WASI support
- **WasmEdge** -- Cloud-native runtime optimized for edge and AI workloads
- **Spin** -- Fermyon's framework for event-driven WASM microservices
- **SpiderLightning (slight)** -- Capability-oriented WASM applications

### Templates

WasmDock ships with project templates for common workloads:

- `http-server-spin` -- HTTP microservice using Fermyon Spin SDK
- `http-server-wasmtime` -- Standalone WASI HTTP server
- `data-processor` -- Stdin/stdout data pipeline
- `edge-function` -- Lightweight edge computing handler

## CLI Reference

| Command | Description |
|---------|-------------|
| `wasmdock doctor` | Check the Docker environment is WASM-ready |
| `wasmdock init <name>` | Scaffold a new WASM project from a template |
| `wasmdock build` | Cross-compile to WASM and package as a Docker image |
| `wasmdock run` | Start the WASM container |
| `wasmdock logs` | Show recent container logs |
| `wasmdock stop` | Stop and remove the container |
| `wasmdock bench` | Benchmark vs a Linux baseline |
| `wasmdock push <ref>` | Push the image to an OCI registry |
| `wasmdock pull <ref>` | Pull a WASM image from an OCI registry |
| `wasmdock templates` | List available templates |
| `wasmdock runtimes` | List supported runtimes |

The CLI is also available as `python -m wasmdock`. See the main
[README](https://github.com/hariharanragothaman/wasmdock#cli-reference) for full option tables.

## Architecture

```
wasmdock/
  cli.py          -- Typer CLI entrypoint
  __main__.py     -- `python -m wasmdock` entry point
  scaffolder.py   -- Jinja2 template rendering
  builder.py      -- Docker build pipeline (cross-compile + package)
  runner.py       -- Container lifecycle management
  benchmarker.py  -- Cold-start, memory, throughput benchmarking
  registry.py     -- OCI push/pull operations
  doctor.py       -- Docker WASM environment diagnostics
  models.py       -- Core dataclasses and enums
  config.py       -- Configuration loading
  templates/      -- Jinja2 project templates
```

## API Reference

### WasmRuntime

```python
from wasmdock.models import WasmRuntime

rt = WasmRuntime.WASMTIME
print(rt.containerd_runtime)  # "io.containerd.wasmtime.v1"
```

### Scaffolder

```python
from wasmdock.scaffolder import Scaffolder
from wasmdock.models import WasmRuntime

s = Scaffolder()
project = s.scaffold("my-app", WasmRuntime.SPIN, template="http-server-spin")
```

### Builder

```python
from wasmdock.builder import Builder

b = Builder()
result = b.build(project)
print(result.image_size_mb)
```

### Benchmarker

```python
from wasmdock.benchmarker import Benchmarker

bench = Benchmarker()
comparison = bench.compare_with_linux(project, "nginx:alpine")
bench.generate_report(comparison, "report.html")
```

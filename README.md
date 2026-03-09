# WasmDock

**Scaffold, build, run, and benchmark WebAssembly containers with Docker's native WASM runtime.**

[![CI](https://github.com/hariharanragothaman/wasmdock/actions/workflows/ci.yml/badge.svg)](https://github.com/hariharanragothaman/wasmdock/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Why WASM Containers?

Docker Desktop 4.15+ supports running WebAssembly workloads natively alongside Linux containers. WASM containers offer dramatic improvements over traditional containers:

| Metric          | WASM Container | Linux Container | Improvement     |
|-----------------|---------------|-----------------|-----------------|
| Cold start      | ~1 ms         | ~300 ms         | 300x faster     |
| Image size      | ~2 MB         | ~50-200 MB      | 25-100x smaller |
| Memory footprint| ~5 MB         | ~30-100 MB      | 6-20x less      |
| Security        | Capability-based sandbox | Namespace isolation | Stronger by default |

WasmDock gives you a batteries-included toolkit to take advantage of these improvements without wrestling with low-level toolchain configuration.

## Prerequisites

- **Docker Desktop 4.15+** with WASM support enabled
  - Settings > Features in development > Enable WASM
  - Settings > General > Use containerd for pulling and storing images
- **Python 3.10+**
- **Rust toolchain** (installed automatically inside Docker build)

## Installation

```bash
pip install wasmdock
```

Or from source:

```bash
git clone https://github.com/hariharanragothaman/wasmdock.git
cd wasmdock
pip install -e ".[dev]"
```

## Quick Start

```bash
# Scaffold a new WASM HTTP service
wasmdock init my-service --runtime wasmtime --template http-server-wasmtime

# Build the WASM module and Docker image
cd my-service
wasmdock build

# Run the container
wasmdock run --port 8080

# Benchmark against a Linux baseline
wasmdock bench --iterations 50 --compare-linux nginx:alpine --output report.html
```

## CLI Reference

### `wasmdock init <name>`

Scaffold a new WASM project from a template.

| Option         | Default               | Description                                   |
|----------------|-----------------------|-----------------------------------------------|
| `--runtime`    | `wasmtime`            | WASM runtime: wasmtime, wasmedge, spin, slight|
| `--language`   | `rust`                | Source language                                |
| `--template`   | `http-server-wasmtime`| Project template                              |
| `--output-dir` | `.`                   | Parent directory for the new project           |

### `wasmdock build`

Build the WASM module and package it as a Docker image.

| Option         | Default | Description                |
|----------------|---------|----------------------------|
| `--project-dir`| `.`     | Path to wasmdock project   |

### `wasmdock run`

Start the WASM container with the correct runtime shim.

| Option         | Default | Description              |
|----------------|---------|--------------------------|
| `--port`       | `8080`  | Host port to bind        |
| `--project-dir`| `.`     | Path to wasmdock project |

### `wasmdock bench`

Run benchmarks on the WASM container.

| Option           | Default | Description                            |
|------------------|---------|----------------------------------------|
| `--iterations`   | `100`   | Number of cold-start iterations        |
| `--compare-linux`| (none)  | Linux image to benchmark against       |
| `--output`       | (none)  | Path for the HTML report               |
| `--project-dir`  | `.`     | Path to wasmdock project               |

### `wasmdock push <target>`

Push the WASM image to an OCI-compliant registry.

```bash
wasmdock push ghcr.io/youruser/my-service:latest
```

### `wasmdock templates`

List all available project templates.

```
+----------------------+-------------------------------------------+---------+------+
| Name                 | Description                               | Runtime | Lang |
+----------------------+-------------------------------------------+---------+------+
| http-server-spin     | HTTP microservice using Fermyon Spin SDK   | spin    | rust |
| http-server-wasmtime | Standalone WASI HTTP server               | wasmtime| rust |
| data-processor       | Stdin/stdout data processing pipeline     | wasmtime| rust |
| edge-function        | Lightweight edge computing request handler| spin    | rust |
+----------------------+-------------------------------------------+---------+------+
```

### `wasmdock runtimes`

List all supported WASM runtimes with their containerd shim identifiers.

## Template Gallery

### HTTP Server (Wasmtime)

A standalone WASI HTTP server targeting the Wasmtime runtime. Best for general-purpose microservices.

```bash
wasmdock init my-api --template http-server-wasmtime --runtime wasmtime
```

### HTTP Server (Spin)

An HTTP microservice built with Fermyon's Spin SDK. Best for event-driven request handlers.

```bash
wasmdock init my-handler --template http-server-spin --runtime spin
```

### Data Processor

A stdin/stdout data pipeline for batch processing workloads. Reads newline-delimited JSON, transforms records, and writes results.

```bash
wasmdock init my-pipeline --template data-processor --runtime wasmtime
```

### Edge Function

A lightweight request handler optimized for edge computing with sub-millisecond cold starts.

```bash
wasmdock init my-edge --template edge-function --runtime spin
```

## Benchmark Example

```bash
wasmdock bench --iterations 50 --compare-linux nginx:alpine --output report.html
```

Sample output:

```
+-------------+-------------------+-------------------+----------------+
| Metric      | WASM (wasmtime)   | Linux             | Improvement    |
+-------------+-------------------+-------------------+----------------+
| Cold Start  |           1.2 ms  |         312.5 ms  | 260.4x faster  |
| Memory      |           4.8 MB  |          48.2 MB  | 90% less       |
| Throughput   |         1,240 rps |         1,180 rps | -              |
| Image Size  |           1.8 MB  |          42.0 MB  | 96% smaller    |
+-------------+-------------------+-------------------+----------------+
```

The `--output` flag generates an interactive HTML report with Plotly bar charts comparing all metrics side-by-side.

## Supported Runtimes

| Runtime                    | Containerd Shim                  | Best For                     |
|----------------------------|----------------------------------|------------------------------|
| Wasmtime                   | `io.containerd.wasmtime.v1`      | General-purpose WASI apps    |
| WasmEdge                   | `io.containerd.wasmedge.v1`      | Edge computing, AI inference |
| Fermyon Spin               | `io.containerd.spin.v2`          | Event-driven microservices   |
| SpiderLightning (slight)   | `io.containerd.slight.v1`        | Capability-oriented apps     |

## Architecture

```
wasmdock
  |-- cli.py           Typer CLI with subcommands
  |-- scaffolder.py     Jinja2 template rendering engine
  |-- builder.py        Docker BuildKit pipeline (cross-compile + package)
  |-- runner.py         Container lifecycle management
  |-- benchmarker.py    Cold-start, memory, throughput benchmarking
  |-- registry.py       OCI registry push/pull
  |-- models.py         Core dataclasses and runtime enum
  |-- config.py         YAML configuration loading
  |-- templates/        Jinja2 project templates
       |-- http_server_spin/
       |-- http_server_wasmtime/
       |-- data_processor/
       |-- edge_function/
```

The build pipeline uses Docker's multi-stage builds: a Rust build stage cross-compiles to `wasm32-wasip1`, and the final stage copies the `.wasm` binary into a `scratch` image with no OS layer. Docker's containerd integration routes execution to the appropriate WASM runtime shim.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and contribution guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.

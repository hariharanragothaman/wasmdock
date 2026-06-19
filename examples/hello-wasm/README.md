# Hello WASM -- WasmDock Quickstart

This example walks through creating, building, and running a minimal WASM HTTP server with WasmDock.

> **This directory is a ready-to-build project.** The `Dockerfile`, `Cargo.toml`,
> `src/main.rs`, and `wasmdock.yml` here are exactly what `wasmdock init` generates,
> so you can skip straight to building. A `Makefile` wraps the common commands:
>
> ```bash
> cd examples/hello-wasm
> make doctor   # verify your Docker WASM environment
> make build    # build the WASM image
> make run      # run it on http://localhost:8080
> make bench    # benchmark vs nginx:alpine
> make stop     # stop and remove the container
> ```

## Prerequisites

- Python 3.10+
- Docker Desktop 4.15+ with WASM support enabled
- containerd image store enabled in Docker Desktop settings

## Step 1: Install WasmDock

```bash
pip install wasmdock
```

## Step 1b: Verify Your Environment

Before building, confirm Docker is set up for WASM:

```bash
wasmdock doctor
```

This checks that the Docker daemon is reachable, the containerd image store is
enabled, and which WASM runtime shims are installed.

## Step 2: Scaffold the Project

```bash
wasmdock init hello-wasm --runtime wasmtime --template http-server-wasmtime
```

This creates a `hello-wasm/` directory with:

```
hello-wasm/
  Dockerfile        # Multi-stage: compile Rust to WASM, package in scratch image
  Cargo.toml        # Rust project with WASI dependencies
  wasmdock.yml      # WasmDock project configuration
  src/
    main.rs         # WASI HTTP handler
```

## Step 3: Build the WASM Image

```bash
cd hello-wasm
wasmdock build
```

The build process:

1. Compiles Rust source to `wasm32-wasip1` target inside a Docker build stage
2. Copies the `.wasm` binary into a `scratch` image (no OS layer)
3. Tags the image as `wasmdock-hello-wasm:latest`

Expected output:

```
Built wasmdock-hello-wasm:latest (1.8 MB) in 42.3s
```

## Step 4: Run the Container

```bash
wasmdock run --port 8080
```

The container starts using Docker's Wasmtime containerd shim. Test it:

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
```

Inspect logs or tear it down:

```bash
wasmdock logs --tail 50
wasmdock stop
```

## Step 5: Benchmark (Optional)

Compare the WASM container against a standard Linux container:

```bash
wasmdock bench --iterations 50 --compare-linux nginx:alpine --output report.html
```

This produces an interactive HTML report with Plotly charts comparing cold-start latency, memory usage, throughput, and image size.

## What's Next

- Try different runtimes: `--runtime spin`, `--runtime wasmedge`
- Try different templates: `--template data-processor`, `--template edge-function`
- Push to a registry: `wasmdock push ghcr.io/youruser/hello-wasm:latest`
- Explore the generated Rust source and customize the handler

# syntax=docker/dockerfile:1
# WasmDock: Wasmtime HTTP server -- multi-stage build
# Runtime: wasmtime (io.containerd.wasmtime.v1)

FROM --platform=$BUILDPLATFORM rust:1.79-slim AS build

RUN rustup target add wasm32-wasip1

WORKDIR /src
COPY Cargo.toml ./
COPY src/ ./src/

RUN cargo build --target wasm32-wasip1 --release

# -------------------------------------------------------------------
# Minimal WASM image
# -------------------------------------------------------------------
FROM scratch

COPY --from=build /src/target/wasm32-wasip1/release/hello_wasm.wasm /hello_wasm.wasm

ENTRYPOINT ["/hello_wasm.wasm"]

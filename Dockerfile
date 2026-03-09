# WasmDock development and CI image
# Includes Python, Rust toolchain, and Docker CLI for end-to-end testing.

FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain with WASM targets
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --default-toolchain stable --profile minimal \
    && . "$HOME/.cargo/env" \
    && rustup target add wasm32-wasip1

ENV PATH="/root/.cargo/bin:${PATH}"

# Install Docker CLI (for Docker-in-Docker or socket-mounted workflows)
RUN curl -fsSL https://get.docker.com | sh

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || true

COPY . .
RUN pip install --no-cache-dir -e ".[dev]"

ENTRYPOINT ["wasmdock"]
CMD ["--help"]

"""WasmDock project templates."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent

TEMPLATE_REGISTRY: dict[str, dict[str, str]] = {
    "http-server-spin": {
        "dir": "http_server_spin",
        "description": "HTTP microservice using Fermyon Spin SDK",
        "runtime": "spin",
        "language": "rust",
    },
    "http-server-wasmtime": {
        "dir": "http_server_wasmtime",
        "description": "Standalone WASI HTTP server targeting Wasmtime",
        "runtime": "wasmtime",
        "language": "rust",
    },
    "data-processor": {
        "dir": "data_processor",
        "description": "Stdin/stdout data processing pipeline",
        "runtime": "wasmtime",
        "language": "rust",
    },
    "data-processor-go": {
        "dir": "data_processor_go",
        "description": "Stdin/stdout data processor written in Go (TinyGo)",
        "runtime": "wasmtime",
        "language": "go",
    },
    "edge-function": {
        "dir": "edge_function",
        "description": "Lightweight edge computing request handler",
        "runtime": "spin",
        "language": "rust",
    },
}


def get_template_dir(template_name: str) -> Path:
    """Resolve a template name to its directory on disk."""
    entry = TEMPLATE_REGISTRY.get(template_name)
    if entry is None:
        raise ValueError(
            f"Unknown template '{template_name}'. Available: {', '.join(TEMPLATE_REGISTRY)}"
        )
    return TEMPLATES_DIR / entry["dir"]

"""WasmDock configuration defaults and project config loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from wasmdock.models import WasmRuntime

_yaml = YAML()
_yaml.preserve_quotes = True

CONFIG_FILENAME = "wasmdock.yml"


@dataclass
class WasmDockConfig:
    """Global defaults that can be overridden per-project."""

    default_runtime: WasmRuntime = WasmRuntime.WASMTIME
    default_language: str = "rust"
    docker_platform: str = "wasi/wasm"
    benchmark_iterations: int = 100
    benchmark_warmup: int = 5
    registry: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def load_project_config(project_dir: Path) -> dict[str, Any]:
    """Load a project-level wasmdock.yml if it exists."""
    config_path = project_dir / CONFIG_FILENAME
    if not config_path.exists():
        return {}
    with config_path.open() as fh:
        data = _yaml.load(fh)
    return dict(data) if data else {}


def save_project_config(project_dir: Path, config: dict[str, Any]) -> Path:
    """Write project configuration to wasmdock.yml."""
    config_path = project_dir / CONFIG_FILENAME
    with config_path.open("w") as fh:
        _yaml.dump(config, fh)
    return config_path


def get_default_config() -> WasmDockConfig:
    """Return the default configuration."""
    return WasmDockConfig()

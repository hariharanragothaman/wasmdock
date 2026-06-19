"""Tests for project configuration loading and saving."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wasmdock.config import (
    get_default_config,
    load_project_config,
    save_project_config,
)
from wasmdock.models import WasmRuntime

if TYPE_CHECKING:
    from pathlib import Path


class TestProjectConfigRoundTrip:
    def test_save_then_load(self, tmp_path: Path) -> None:
        payload = {
            "name": "demo",
            "runtime": "spin",
            "language": "rust",
            "template": "http-server-spin",
        }
        path = save_project_config(tmp_path, payload)
        assert path.exists()
        assert path.name == "wasmdock.yml"

        loaded = load_project_config(tmp_path)
        assert loaded["name"] == "demo"
        assert loaded["runtime"] == "spin"

    def test_load_missing_returns_empty_dict(self, tmp_path: Path) -> None:
        assert load_project_config(tmp_path) == {}


class TestDefaults:
    def test_default_config(self) -> None:
        cfg = get_default_config()
        assert cfg.default_runtime is WasmRuntime.WASMTIME
        assert cfg.docker_platform == "wasi/wasm"
        assert cfg.benchmark_iterations == 100

"""Core data models for WasmDock."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class WasmRuntime(str, Enum):
    """Supported WebAssembly container runtimes."""

    WASMTIME = "wasmtime"
    WASMEDGE = "wasmedge"
    SPIN = "spin"
    SLIGHT = "slight"

    @property
    def containerd_runtime(self) -> str:
        """Return the containerd shim identifier for this runtime."""
        return _CONTAINERD_RUNTIMES[self]

    @property
    def display_name(self) -> str:
        return _DISPLAY_NAMES[self]

    @property
    def description(self) -> str:
        return _DESCRIPTIONS[self]


_CONTAINERD_RUNTIMES: dict[WasmRuntime, str] = {
    WasmRuntime.WASMTIME: "io.containerd.wasmtime.v1",
    WasmRuntime.WASMEDGE: "io.containerd.wasmedge.v1",
    WasmRuntime.SPIN: "io.containerd.spin.v2",
    WasmRuntime.SLIGHT: "io.containerd.slight.v1",
}

_DISPLAY_NAMES: dict[WasmRuntime, str] = {
    WasmRuntime.WASMTIME: "Wasmtime",
    WasmRuntime.WASMEDGE: "WasmEdge",
    WasmRuntime.SPIN: "Fermyon Spin",
    WasmRuntime.SLIGHT: "Deislabs SpiderLightning",
}

_DESCRIPTIONS: dict[WasmRuntime, str] = {
    WasmRuntime.WASMTIME: "Bytecode Alliance reference runtime with broad WASI support",
    WasmRuntime.WASMEDGE: "Cloud-native WASM runtime optimized for edge and AI workloads",
    WasmRuntime.SPIN: "Fermyon's framework for building event-driven WASM microservices",
    WasmRuntime.SLIGHT: "Deislabs SpiderLightning for capability-oriented WASM apps",
}


@dataclass
class WasmProject:
    """Represents a scaffolded WASM project on disk."""

    name: str
    runtime: WasmRuntime
    language: str
    template: str
    project_dir: Path

    @property
    def image_name(self) -> str:
        return f"wasmdock-{self.name}:latest"


@dataclass
class BuildResult:
    """Outcome of a WASM container build."""

    success: bool
    image_name: str
    image_size_mb: float = 0.0
    build_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    """Outcome of launching a WASM container."""

    container_id: str
    port: int
    runtime: str


@dataclass
class BenchmarkResult:
    """Performance measurements for a single runtime target."""

    runtime: str
    cold_start_ms: float
    memory_mb: float
    throughput_rps: float
    image_size_mb: float
    iterations: int


@dataclass
class BenchmarkComparison:
    """Side-by-side comparison of WASM vs Linux container performance."""

    wasm_result: BenchmarkResult
    linux_result: BenchmarkResult

    @property
    def cold_start_speedup(self) -> float:
        if self.wasm_result.cold_start_ms == 0:
            return 0.0
        return self.linux_result.cold_start_ms / self.wasm_result.cold_start_ms

    @property
    def memory_reduction_percent(self) -> float:
        if self.linux_result.memory_mb == 0:
            return 0.0
        return (
            (self.linux_result.memory_mb - self.wasm_result.memory_mb)
            / self.linux_result.memory_mb
            * 100
        )

    @property
    def size_reduction_percent(self) -> float:
        if self.linux_result.image_size_mb == 0:
            return 0.0
        return (
            (self.linux_result.image_size_mb - self.wasm_result.image_size_mb)
            / self.linux_result.image_size_mb
            * 100
        )

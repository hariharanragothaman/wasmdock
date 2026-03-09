"""Tests for the WasmDock benchmarker (mocked Docker interactions)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wasmdock.benchmarker import Benchmarker
from wasmdock.models import BenchmarkComparison, BenchmarkResult


@pytest.fixture
def benchmarker() -> Benchmarker:
    with patch("wasmdock.benchmarker.docker") as mock_docker:
        mock_docker.from_env.return_value = MagicMock()
        b = Benchmarker()
    return b


class TestColdStartMeasurement:
    def test_cold_start_returns_list_of_floats(self, benchmarker: Benchmarker) -> None:
        mock_container = MagicMock()
        mock_container.id = "abc123"
        benchmarker._client.containers.create.return_value = mock_container

        with patch.object(benchmarker, "_wait_for_http"):
            results = benchmarker.benchmark_cold_start(
                "test-image:latest",
                "io.containerd.wasmtime.v1",
                iterations=3,
                port=19090,
            )

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(t, float) for t in results)

    def test_cold_start_handles_docker_failure(self, benchmarker: Benchmarker) -> None:
        from docker.errors import DockerException

        benchmarker._client.containers.create.side_effect = DockerException("fail")

        with patch.object(benchmarker, "_wait_for_http"):
            results = benchmarker.benchmark_cold_start(
                "bad-image:latest",
                "io.containerd.wasmtime.v1",
                iterations=2,
                port=19091,
            )

        assert results == []


class TestComparisonCalculation:
    def test_cold_start_speedup(self) -> None:
        wasm = BenchmarkResult(
            runtime="wasmtime",
            cold_start_ms=10.0,
            memory_mb=5.0,
            throughput_rps=1000.0,
            image_size_mb=2.0,
            iterations=100,
        )
        linux = BenchmarkResult(
            runtime="linux",
            cold_start_ms=500.0,
            memory_mb=50.0,
            throughput_rps=800.0,
            image_size_mb=100.0,
            iterations=100,
        )
        comparison = BenchmarkComparison(wasm_result=wasm, linux_result=linux)

        assert comparison.cold_start_speedup == 50.0
        assert comparison.memory_reduction_percent == 90.0
        assert comparison.size_reduction_percent == 98.0

    def test_comparison_with_zero_linux_values(self) -> None:
        wasm = BenchmarkResult(
            runtime="wasmtime",
            cold_start_ms=10.0,
            memory_mb=5.0,
            throughput_rps=1000.0,
            image_size_mb=2.0,
            iterations=100,
        )
        linux = BenchmarkResult(
            runtime="linux",
            cold_start_ms=0.0,
            memory_mb=0.0,
            throughput_rps=0.0,
            image_size_mb=0.0,
            iterations=100,
        )
        comparison = BenchmarkComparison(wasm_result=wasm, linux_result=linux)

        assert comparison.memory_reduction_percent == 0.0
        assert comparison.size_reduction_percent == 0.0


class TestReportGeneration:
    def test_generate_report_creates_html(
        self, benchmarker: Benchmarker, tmp_path: Path
    ) -> None:
        wasm = BenchmarkResult(
            runtime="wasmtime",
            cold_start_ms=12.5,
            memory_mb=4.2,
            throughput_rps=950.0,
            image_size_mb=1.8,
            iterations=50,
        )
        linux = BenchmarkResult(
            runtime="linux",
            cold_start_ms=450.0,
            memory_mb=48.0,
            throughput_rps=820.0,
            image_size_mb=95.0,
            iterations=50,
        )
        comparison = BenchmarkComparison(wasm_result=wasm, linux_result=linux)

        output = tmp_path / "report.html"
        result_path = benchmarker.generate_report(comparison, str(output))

        assert result_path.exists()
        content = result_path.read_text()
        assert "plotly" in content.lower()
        assert "WasmDock Benchmark" in content

    def test_print_comparison_runs_without_error(
        self, benchmarker: Benchmarker
    ) -> None:
        wasm = BenchmarkResult(
            runtime="wasmtime",
            cold_start_ms=15.0,
            memory_mb=6.0,
            throughput_rps=900.0,
            image_size_mb=2.5,
            iterations=10,
        )
        linux = BenchmarkResult(
            runtime="linux",
            cold_start_ms=400.0,
            memory_mb=45.0,
            throughput_rps=750.0,
            image_size_mb=80.0,
            iterations=10,
        )
        comparison = BenchmarkComparison(wasm_result=wasm, linux_result=linux)
        Benchmarker.print_comparison(comparison)

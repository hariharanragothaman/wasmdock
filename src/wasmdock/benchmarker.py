"""Benchmark engine for comparing WASM and Linux container performance."""

from __future__ import annotations

import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

import docker
import plotly.graph_objects as go
from docker.errors import DockerException
from plotly.subplots import make_subplots
from rich.console import Console
from rich.table import Table

from wasmdock.models import BenchmarkComparison, BenchmarkResult, WasmProject

console = Console()


class Benchmarker:
    """Measures cold-start latency, memory, throughput, and image size."""

    def __init__(self) -> None:
        self._client = docker.from_env()

    # ------------------------------------------------------------------
    # Individual benchmark primitives
    # ------------------------------------------------------------------

    def benchmark_cold_start(
        self,
        image_name: str,
        runtime: str,
        iterations: int = 100,
        port: int = 9090,
    ) -> list[float]:
        """Measure cold-start time across *iterations* container cycles.

        Each iteration: create container -> start -> wait for first HTTP
        response on *port* -> record elapsed ms -> stop & remove.
        """
        times: list[float] = []

        for i in range(iterations):
            try:
                container = self._client.containers.create(
                    image_name,
                    detach=True,
                    ports={"8080/tcp": port},
                    platform="wasi/wasm",
                    runtime=runtime,
                )

                start = time.perf_counter()
                container.start()

                self._wait_for_http(port, timeout=30)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(round(elapsed_ms, 2))
            except DockerException as exc:
                console.print(f"[yellow]Iteration {i} failed: {exc}[/yellow]")
            finally:
                try:
                    container.stop(timeout=1)
                    container.remove(force=True)
                except Exception:
                    pass

            if (i + 1) % 10 == 0:
                console.print(f"  cold-start: {i + 1}/{iterations} iterations")

        return times

    def benchmark_memory(self, container_id: str) -> float:
        """Read current memory usage (MB) from Docker stats API."""
        try:
            container = self._client.containers.get(container_id)
            stats = container.stats(stream=False)
            usage_bytes = float(stats["memory_stats"].get("usage", 0))
            return round(usage_bytes / (1024 * 1024), 2)
        except (DockerException, KeyError):
            return 0.0

    def benchmark_throughput(
        self,
        endpoint: str,
        duration_seconds: int = 10,
    ) -> float:
        """Simple HTTP throughput benchmark using stdlib urllib.

        Sends sequential GET requests for *duration_seconds* and returns
        requests-per-second.
        """
        count = 0
        deadline = time.monotonic() + duration_seconds
        while time.monotonic() < deadline:
            try:
                req = urllib.request.Request(endpoint, method="GET")
                with urllib.request.urlopen(req, timeout=5):
                    count += 1
            except (urllib.error.URLError, OSError):
                pass
        rps = count / duration_seconds if duration_seconds > 0 else 0
        return round(rps, 2)

    # ------------------------------------------------------------------
    # High-level benchmark orchestration
    # ------------------------------------------------------------------

    def benchmark(
        self,
        project: WasmProject,
        iterations: int = 100,
        warmup: int = 5,
        port: int = 9090,
    ) -> BenchmarkResult:
        """Run the full benchmark suite for a WASM project."""
        image_name = project.image_name
        runtime = project.runtime.containerd_runtime

        console.print(f"[bold]Benchmarking {image_name}[/bold]")

        # Warmup
        if warmup > 0:
            console.print(f"  warming up ({warmup} iterations)...")
            self.benchmark_cold_start(image_name, runtime, warmup, port)

        # Cold start
        console.print(f"  measuring cold start ({iterations} iterations)...")
        cold_starts = self.benchmark_cold_start(image_name, runtime, iterations, port)
        cold_start_median = statistics.median(cold_starts) if cold_starts else 0.0

        # Memory & throughput (run a long-lived container)
        memory_mb = 0.0
        throughput_rps = 0.0
        container = None
        try:
            container = self._client.containers.run(
                image_name,
                detach=True,
                ports={"8080/tcp": port},
                platform="wasi/wasm",
                runtime=runtime,
            )
            self._wait_for_http(port, timeout=30)

            memory_mb = self.benchmark_memory(container.id)

            endpoint = f"http://localhost:{port}/"
            console.print("  measuring throughput (10s)...")
            throughput_rps = self.benchmark_throughput(endpoint, duration_seconds=10)
        except DockerException as exc:
            console.print(f"[yellow]Benchmark container error: {exc}[/yellow]")
        finally:
            if container:
                try:
                    container.stop(timeout=1)
                    container.remove(force=True)
                except Exception:
                    pass

        image_size = self._image_size_mb(image_name)

        return BenchmarkResult(
            runtime=project.runtime.value,
            cold_start_ms=round(cold_start_median, 2),
            memory_mb=memory_mb,
            throughput_rps=throughput_rps,
            image_size_mb=image_size,
            iterations=iterations,
        )

    def compare_with_linux(
        self,
        wasm_project: WasmProject,
        linux_image: str,
        iterations: int = 100,
        warmup: int = 5,
        port: int = 9090,
    ) -> BenchmarkComparison:
        """Benchmark both a WASM container and a Linux container."""
        wasm_result = self.benchmark(wasm_project, iterations, warmup, port)

        console.print(f"[bold]Benchmarking Linux baseline: {linux_image}[/bold]")

        linux_cold_starts = self._benchmark_linux_cold_start(linux_image, iterations, port)
        linux_cold_median = statistics.median(linux_cold_starts) if linux_cold_starts else 0.0

        linux_memory = 0.0
        linux_throughput = 0.0
        container = None
        try:
            container = self._client.containers.run(
                linux_image,
                detach=True,
                ports={"8080/tcp": port},
            )
            self._wait_for_http(port, timeout=30)
            linux_memory = self.benchmark_memory(container.id)
            linux_throughput = self.benchmark_throughput(
                f"http://localhost:{port}/", duration_seconds=10
            )
        except DockerException as exc:
            console.print(f"[yellow]Linux benchmark error: {exc}[/yellow]")
        finally:
            if container:
                try:
                    container.stop(timeout=1)
                    container.remove(force=True)
                except Exception:
                    pass

        linux_size = self._image_size_mb(linux_image)

        linux_result = BenchmarkResult(
            runtime="linux",
            cold_start_ms=round(linux_cold_median, 2),
            memory_mb=linux_memory,
            throughput_rps=linux_throughput,
            image_size_mb=linux_size,
            iterations=iterations,
        )

        comparison = BenchmarkComparison(
            wasm_result=wasm_result,
            linux_result=linux_result,
        )

        self.print_comparison(comparison)
        return comparison

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(
        self,
        comparison: BenchmarkComparison,
        output_path: str = "benchmark_report.html",
    ) -> Path:
        """Generate an interactive HTML report with Plotly charts."""
        wasm = comparison.wasm_result
        linux = comparison.linux_result
        categories = ["Cold Start (ms)", "Memory (MB)", "Throughput (rps)", "Image Size (MB)"]

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=categories,
        )

        pairs = [
            (wasm.cold_start_ms, linux.cold_start_ms),
            (wasm.memory_mb, linux.memory_mb),
            (wasm.throughput_rps, linux.throughput_rps),
            (wasm.image_size_mb, linux.image_size_mb),
        ]

        positions = [(1, 1), (1, 2), (2, 1), (2, 2)]

        for (wval, lval), (row, col) in zip(pairs, positions, strict=True):
            fig.add_trace(
                go.Bar(
                    x=["WASM", "Linux"],
                    y=[wval, lval],
                    marker_color=["#00d4aa", "#ff6b6b"],
                    showlegend=False,
                ),
                row=row,
                col=col,
            )

        fig.update_layout(
            title_text=(
                f"WasmDock Benchmark: {wasm.runtime} vs Linux ({wasm.iterations} iterations)"
            ),
            template="plotly_dark",
            height=700,
        )

        outpath = Path(output_path)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(outpath), include_plotlyjs="cdn")

        console.print(f"[green]Report saved to {outpath}[/green]")
        return outpath

    @staticmethod
    def print_comparison(comparison: BenchmarkComparison) -> None:
        """Print a Rich table summarising the comparison."""
        wasm = comparison.wasm_result
        linux = comparison.linux_result

        table = Table(title="WasmDock Benchmark Results", show_lines=True)
        table.add_column("Metric", style="bold")
        table.add_column(f"WASM ({wasm.runtime})", justify="right", style="cyan")
        table.add_column("Linux", justify="right", style="red")
        table.add_column("Improvement", justify="right", style="green")

        table.add_row(
            "Cold Start",
            f"{wasm.cold_start_ms:.1f} ms",
            f"{linux.cold_start_ms:.1f} ms",
            f"{comparison.cold_start_speedup:.1f}x faster",
        )
        table.add_row(
            "Memory",
            f"{wasm.memory_mb:.1f} MB",
            f"{linux.memory_mb:.1f} MB",
            f"{comparison.memory_reduction_percent:.0f}% less",
        )
        table.add_row(
            "Throughput",
            f"{wasm.throughput_rps:.0f} rps",
            f"{linux.throughput_rps:.0f} rps",
            "-",
        )
        table.add_row(
            "Image Size",
            f"{wasm.image_size_mb:.1f} MB",
            f"{linux.image_size_mb:.1f} MB",
            f"{comparison.size_reduction_percent:.0f}% smaller",
        )

        console.print(table)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _benchmark_linux_cold_start(
        self,
        image_name: str,
        iterations: int,
        port: int,
    ) -> list[float]:
        """Measure cold-start for a standard Linux container."""
        times: list[float] = []
        for i in range(iterations):
            container = None
            try:
                container = self._client.containers.create(
                    image_name,
                    detach=True,
                    ports={"8080/tcp": port},
                )
                start = time.perf_counter()
                container.start()
                self._wait_for_http(port, timeout=30)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(round(elapsed_ms, 2))
            except DockerException as exc:
                console.print(f"[yellow]Linux iteration {i} failed: {exc}[/yellow]")
            finally:
                if container:
                    try:
                        container.stop(timeout=1)
                        container.remove(force=True)
                    except Exception:
                        pass

            if (i + 1) % 10 == 0:
                console.print(f"  linux cold-start: {i + 1}/{iterations} iterations")

        return times

    @staticmethod
    def _wait_for_http(port: int, timeout: float = 30) -> None:
        """Block until an HTTP server responds on localhost:port."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                req = urllib.request.Request(f"http://localhost:{port}/", method="GET")
                with urllib.request.urlopen(req, timeout=2):
                    return
            except (urllib.error.URLError, OSError):
                time.sleep(0.25)

    def _image_size_mb(self, image_name: str) -> float:
        try:
            image = self._client.images.get(image_name)
            return round(float(image.attrs.get("Size", 0)) / (1024 * 1024), 2)
        except DockerException:
            return 0.0

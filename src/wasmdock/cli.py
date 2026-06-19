"""WasmDock CLI -- scaffold, build, run, and benchmark WASM containers."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from wasmdock import __version__
from wasmdock.models import WasmRuntime

app = typer.Typer(
    name="wasmdock",
    help="Docker-Native WASM Development Toolkit. "
    "Scaffold, build, run, and benchmark WebAssembly containers.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"wasmdock {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """WasmDock -- Docker-Native WASM Development Toolkit."""


# ── init ────────────────────────────────────────────────────────────


@app.command()
def init(
    name: Annotated[str, typer.Argument(help="Project name")],
    runtime: Annotated[
        str | None,
        typer.Option(
            "--runtime",
            "-r",
            help="WASM runtime (defaults to the template's runtime)",
        ),
    ] = None,
    language: Annotated[
        str,
        typer.Option("--language", "-l", help="Source language"),
    ] = "rust",
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="Project template (http-server-spin/http-server-wasmtime/data-processor/edge-function)",
        ),
    ] = "http-server-wasmtime",
    output_dir: Annotated[
        str,
        typer.Option("--output-dir", "-o", help="Parent directory for the new project"),
    ] = ".",
) -> None:
    """Scaffold a new WASM project."""
    from wasmdock.scaffolder import Scaffolder
    from wasmdock.templates import TEMPLATE_REGISTRY

    if template not in TEMPLATE_REGISTRY:
        available = ", ".join(TEMPLATE_REGISTRY)
        console.print(f"[red]Unknown template '{template}'. Available: {available}[/red]")
        raise typer.Exit(1)

    # When no runtime is given, infer the one the template targets.
    if runtime is None:
        runtime = TEMPLATE_REGISTRY[template]["runtime"]

    try:
        wasm_runtime = WasmRuntime(runtime)
    except ValueError:
        console.print(
            f"[red]Unknown runtime '{runtime}'. Use: wasmtime, wasmedge, spin, slight[/red]"
        )
        raise typer.Exit(1) from None

    scaffolder = Scaffolder()
    try:
        scaffolder.scaffold(name, wasm_runtime, language, template, output_dir)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None


# ── build ───────────────────────────────────────────────────────────


@app.command()
def build(
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Path to wasmdock project"),
    ] = ".",
) -> None:
    """Build the WASM module and Docker image."""
    from wasmdock.builder import Builder

    builder = Builder()
    result = builder.build_from_dir(project_dir)
    if not result.success:
        for err in result.errors:
            console.print(f"[red]{err}[/red]")
        raise typer.Exit(1)


# ── run ─────────────────────────────────────────────────────────────


@app.command()
def run(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Host port to bind"),
    ] = 8080,
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Path to wasmdock project"),
    ] = ".",
) -> None:
    """Run the WASM container."""
    from wasmdock.runner import Runner

    runner = Runner()
    result = runner.run_from_dir(project_dir, port=port)
    console.print(f"Container: {result.container_id[:12]}")
    console.print(f"Listening on: http://localhost:{result.port}")


# ── stop ────────────────────────────────────────────────────────────


@app.command()
def stop(
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Path to wasmdock project"),
    ] = ".",
) -> None:
    """Stop and remove the project's running WASM container."""
    from wasmdock.runner import Runner

    runner = Runner()
    try:
        runner.stop_from_dir(project_dir)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None


# ── logs ────────────────────────────────────────────────────────────


@app.command()
def logs(
    tail: Annotated[
        int,
        typer.Option("--tail", "-n", help="Number of trailing log lines to show"),
    ] = 100,
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Path to wasmdock project"),
    ] = ".",
) -> None:
    """Show recent logs from the project's WASM container."""
    from wasmdock.runner import Runner

    runner = Runner()
    try:
        console.print(runner.logs_from_dir(project_dir, tail=tail))
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None


# ── ps ──────────────────────────────────────────────────────────────


@app.command()
def ps() -> None:
    """List WasmDock-managed containers."""
    from wasmdock.runner import Runner

    rows = Runner().list_containers()
    if not rows:
        console.print("No WasmDock containers found.")
        return

    table = Table(title="WasmDock Containers")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Image")
    table.add_column("Ports", style="yellow")
    for row in rows:
        table.add_row(row["name"], row["status"], row["image"], row["ports"])
    console.print(table)


# ── clean ───────────────────────────────────────────────────────────


@app.command()
def clean(
    images: Annotated[
        bool,
        typer.Option("--images", "-i", help="Also remove the project's WASM image"),
    ] = False,
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Path to wasmdock project"),
    ] = ".",
) -> None:
    """Stop the project's container and optionally remove its image."""
    from wasmdock.runner import Runner

    runner = Runner()
    try:
        runner.clean_from_dir(project_dir, remove_image=images)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None


# ── bench ───────────────────────────────────────────────────────────


@app.command()
def bench(
    iterations: Annotated[
        int,
        typer.Option("--iterations", "-n", help="Number of benchmark iterations"),
    ] = 100,
    compare_linux: Annotated[
        str | None,
        typer.Option("--compare-linux", help="Linux image to compare against"),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="HTML report output path"),
    ] = None,
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Path to wasmdock project"),
    ] = ".",
) -> None:
    """Benchmark the WASM container."""
    from wasmdock.benchmarker import Benchmarker
    from wasmdock.config import load_project_config
    from wasmdock.models import WasmProject

    path = Path(project_dir).resolve()
    config = load_project_config(path)
    if not config:
        console.print(f"[red]No wasmdock.yml found in {path}[/red]")
        raise typer.Exit(1)

    project = WasmProject(
        name=config["name"],
        runtime=WasmRuntime(config["runtime"]),
        language=config.get("language", "rust"),
        template=config.get("template", "http-server-wasmtime"),
        project_dir=path,
    )

    benchmarker = Benchmarker()

    if compare_linux:
        comparison = benchmarker.compare_with_linux(project, compare_linux, iterations=iterations)
        if output:
            benchmarker.generate_report(comparison, output)
    else:
        result = benchmarker.benchmark(project, iterations=iterations)
        console.print(f"Cold start (median): [cyan]{result.cold_start_ms:.1f} ms[/cyan]")
        console.print(f"Memory:              [cyan]{result.memory_mb:.1f} MB[/cyan]")
        console.print(f"Throughput:          [cyan]{result.throughput_rps:.0f} rps[/cyan]")
        console.print(f"Image size:          [cyan]{result.image_size_mb:.1f} MB[/cyan]")


# ── push ────────────────────────────────────────────────────────────


@app.command()
def push(
    target: Annotated[str, typer.Argument(help="Registry target (e.g. ghcr.io/user/app:latest)")],
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Path to wasmdock project"),
    ] = ".",
) -> None:
    """Push the WASM image to an OCI registry."""
    from wasmdock.config import load_project_config
    from wasmdock.registry import Registry

    path = Path(project_dir).resolve()
    config = load_project_config(path)
    if not config:
        console.print(f"[red]No wasmdock.yml found in {path}[/red]")
        raise typer.Exit(1)

    image_name = f"wasmdock-{config['name']}:latest"
    registry = Registry()
    registry.push(image_name, target)


# ── pull ────────────────────────────────────────────────────────────


@app.command()
def pull(
    reference: Annotated[
        str, typer.Argument(help="Image reference (e.g. ghcr.io/user/app:latest)")
    ],
) -> None:
    """Pull a WASM image from an OCI registry."""
    from wasmdock.registry import Registry

    registry = Registry()
    registry.pull(reference)


# ── templates ───────────────────────────────────────────────────────


@app.command()
def templates() -> None:
    """List available project templates."""
    from wasmdock.scaffolder import Scaffolder

    scaffolder = Scaffolder()
    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Runtime", style="green")
    table.add_column("Language", style="yellow")

    for tmpl in scaffolder.list_templates():
        table.add_row(tmpl["name"], tmpl["description"], tmpl["runtime"], tmpl["language"])

    console.print(table)


# ── runtimes ────────────────────────────────────────────────────────


@app.command()
def runtimes() -> None:
    """List supported WASM runtimes."""
    from wasmdock.scaffolder import Scaffolder

    scaffolder = Scaffolder()
    table = Table(title="Supported WASM Runtimes")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name", style="bold")
    table.add_column("Containerd Runtime", style="green")
    table.add_column("Description")

    for rt in scaffolder.list_runtimes():
        table.add_row(rt["name"], rt["display_name"], rt["containerd_runtime"], rt["description"])

    console.print(table)


# ── doctor ──────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
    """Check that the local Docker environment is ready for WASM containers."""
    from wasmdock.doctor import Doctor

    if not Doctor().report():
        raise typer.Exit(1)

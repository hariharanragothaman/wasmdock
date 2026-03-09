"""WASM container build pipeline."""

from __future__ import annotations

import time
from pathlib import Path

import docker
from docker.errors import BuildError, DockerException
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from wasmdock.config import load_project_config
from wasmdock.models import BuildResult, WasmProject, WasmRuntime

console = Console()


class Builder:
    """Builds WASM modules and Docker images."""

    def __init__(self) -> None:
        self._client = docker.from_env()

    def build(self, project: WasmProject) -> BuildResult:
        """Compile source to WASM and package as a Docker image.

        Uses Docker's BuildKit multi-stage build to cross-compile
        Rust to the ``wasm32-wasip1`` target, then produces a minimal
        ``scratch``-based image annotated with the correct WASM platform.
        """
        image_name = project.image_name
        dockerfile_path = project.project_dir / "Dockerfile"

        if not dockerfile_path.exists():
            return BuildResult(
                success=False,
                image_name=image_name,
                errors=[f"Dockerfile not found at {dockerfile_path}"],
            )

        start = time.monotonic()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Building {image_name}...", total=None)

            try:
                image, build_logs = self._client.images.build(
                    path=str(project.project_dir),
                    tag=image_name,
                    dockerfile="Dockerfile",
                    platform="wasi/wasm",
                    rm=True,
                )
            except BuildError as exc:
                elapsed = time.monotonic() - start
                error_lines = [
                    line.get("error", "")
                    for line in exc.build_log
                    if line.get("error")
                ]
                return BuildResult(
                    success=False,
                    image_name=image_name,
                    build_time_seconds=round(elapsed, 2),
                    errors=error_lines or [str(exc)],
                )
            except DockerException as exc:
                elapsed = time.monotonic() - start
                return BuildResult(
                    success=False,
                    image_name=image_name,
                    build_time_seconds=round(elapsed, 2),
                    errors=[str(exc)],
                )

            progress.update(task, completed=True)

        elapsed = time.monotonic() - start
        size_bytes = image.attrs.get("Size", 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)

        console.print(f"[green]Built {image_name} ({size_mb} MB) in {elapsed:.1f}s[/green]")

        return BuildResult(
            success=True,
            image_name=image_name,
            image_size_mb=size_mb,
            build_time_seconds=round(elapsed, 2),
        )

    def build_from_dir(self, project_dir: str = ".") -> BuildResult:
        """Load project config from a directory and build."""
        path = Path(project_dir).resolve()
        config = load_project_config(path)
        if not config:
            return BuildResult(
                success=False,
                image_name="unknown",
                errors=[f"No wasmdock.yml found in {path}"],
            )

        project = WasmProject(
            name=config["name"],
            runtime=WasmRuntime(config["runtime"]),
            language=config.get("language", "rust"),
            template=config.get("template", "http-server-wasmtime"),
            project_dir=path,
        )
        return self.build(project)

    def get_image_size(self, image_name: str) -> float:
        """Return image size in MB."""
        try:
            image = self._client.images.get(image_name)
            return round(image.attrs.get("Size", 0) / (1024 * 1024), 2)
        except DockerException:
            return 0.0

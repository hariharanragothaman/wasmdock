"""WASM container build pipeline."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import docker
from docker.errors import DockerException
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

        Delegates to ``docker build`` so the build runs through BuildKit.
        BuildKit is required here: the templates use ``$BUILDPLATFORM`` for
        cross-compilation, which the legacy (docker-py) build endpoint does
        not populate. The result is a minimal ``scratch``-based image built
        for the ``wasi/wasm`` platform.
        """
        image_name = project.image_name
        dockerfile_path = project.project_dir / "Dockerfile"

        if not dockerfile_path.exists():
            return BuildResult(
                success=False,
                image_name=image_name,
                errors=[f"Dockerfile not found at {dockerfile_path}"],
            )

        cmd = [
            "docker",
            "build",
            "--platform",
            "wasi/wasm",
            "--tag",
            image_name,
            "--file",
            str(dockerfile_path),
            str(project.project_dir),
        ]
        # Force BuildKit even on daemons where it is not the default.
        env = {**os.environ, "DOCKER_BUILDKIT": "1"}

        start = time.monotonic()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Building {image_name}...", total=None)
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                    check=False,
                )
            except FileNotFoundError:
                return BuildResult(
                    success=False,
                    image_name=image_name,
                    build_time_seconds=round(time.monotonic() - start, 2),
                    errors=["docker CLI not found on PATH"],
                )
            progress.update(task, completed=True)

        elapsed = round(time.monotonic() - start, 2)

        if proc.returncode != 0:
            stderr_lines = [line for line in proc.stderr.splitlines() if line.strip()]
            return BuildResult(
                success=False,
                image_name=image_name,
                build_time_seconds=elapsed,
                # Keep the tail; BuildKit prints the actionable error last.
                errors=stderr_lines[-15:] or [proc.stdout.strip() or "docker build failed"],
            )

        size_mb = self.get_image_size(image_name)
        console.print(f"[green]Built {image_name} ({size_mb} MB) in {elapsed:.1f}s[/green]")

        return BuildResult(
            success=True,
            image_name=image_name,
            image_size_mb=size_mb,
            build_time_seconds=elapsed,
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
            return round(float(image.attrs.get("Size", 0)) / (1024 * 1024), 2)
        except DockerException:
            return 0.0

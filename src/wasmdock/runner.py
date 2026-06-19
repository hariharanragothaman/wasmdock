"""WASM container runner."""

from __future__ import annotations

import time
from pathlib import Path

import docker
from docker.errors import DockerException
from rich.console import Console

from wasmdock.config import load_project_config
from wasmdock.models import RunResult, WasmProject, WasmRuntime

console = Console()

_READINESS_TIMEOUT_SECONDS = 30
_READINESS_POLL_INTERVAL = 0.5


class Runner:
    """Manages the lifecycle of WASM containers."""

    def __init__(self) -> None:
        self._client = docker.from_env()

    def run(
        self,
        project: WasmProject,
        port: int = 8080,
        detach: bool = True,
    ) -> RunResult:
        """Start a WASM container with the correct runtime shim.

        The container is launched with ``--platform wasi/wasm`` and
        the appropriate containerd runtime flag so Docker delegates
        execution to the WASM runtime instead of runc.
        """
        image_name = project.image_name
        runtime_str = project.runtime.containerd_runtime
        container_name = f"wasmdock-{project.name}"

        # Make `run` idempotent: drop any prior container with the same name
        # so re-running does not fail with a name conflict.
        self._remove_existing(container_name)

        try:
            container = self._client.containers.run(
                image_name,
                detach=detach,
                ports={"8080/tcp": port},
                platform="wasi/wasm",
                runtime=runtime_str,
                name=container_name,
                remove=False,
            )
        except DockerException as exc:
            console.print(f"[red]Failed to start container: {exc}[/red]")
            raise

        container_id = container.id
        console.print(
            f"[green]Container {container_id[:12]} started "
            f"on port {port} (runtime: {project.runtime.value})[/green]"
        )

        self._wait_for_ready(container_id)

        return RunResult(
            container_id=container_id,
            port=port,
            runtime=runtime_str,
        )

    def run_from_dir(self, project_dir: str = ".", port: int = 8080) -> RunResult:
        """Load project config from a directory and run."""
        path = Path(project_dir).resolve()
        config = load_project_config(path)
        if not config:
            raise FileNotFoundError(f"No wasmdock.yml found in {path}")

        project = WasmProject(
            name=config["name"],
            runtime=WasmRuntime(config["runtime"]),
            language=config.get("language", "rust"),
            template=config.get("template", "http-server-wasmtime"),
            project_dir=path,
        )
        return self.run(project, port=port)

    def stop(self, container_id: str) -> None:
        """Stop and remove a running container."""
        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True)
            console.print(f"[yellow]Container {container_id[:12]} stopped[/yellow]")
        except DockerException as exc:
            console.print(f"[red]Error stopping container: {exc}[/red]")

    def stop_from_dir(self, project_dir: str = ".") -> None:
        """Stop the container associated with a project directory."""
        self.stop(self._container_name_from_dir(project_dir))

    def list_containers(self) -> list[dict[str, str]]:
        """Return metadata for every WasmDock-managed container."""
        containers = self._client.containers.list(all=True, filters={"name": "wasmdock-"})
        rows: list[dict[str, str]] = []
        for c in containers:
            tags = c.image.tags if c.image else []
            rows.append(
                {
                    "name": c.name,
                    "status": c.status,
                    "image": tags[0] if tags else c.attrs.get("Image", ""),
                    "ports": self._format_ports(c.ports),
                }
            )
        return rows

    def clean_from_dir(self, project_dir: str = ".", remove_image: bool = False) -> None:
        """Stop the project's container and optionally remove its image."""
        path = Path(project_dir).resolve()
        config = load_project_config(path)
        if not config:
            raise FileNotFoundError(f"No wasmdock.yml found in {path}")

        self.stop(f"wasmdock-{config['name']}")
        if remove_image:
            image_name = f"wasmdock-{config['name']}:latest"
            try:
                self._client.images.remove(image_name, force=True)
                console.print(f"[yellow]Removed image {image_name}[/yellow]")
            except DockerException as exc:
                console.print(f"[red]Could not remove image {image_name}: {exc}[/red]")

    def logs_from_dir(self, project_dir: str = ".", tail: int = 100) -> str:
        """Return logs for the container associated with a project directory."""
        return self.logs(self._container_name_from_dir(project_dir), tail=tail)

    @staticmethod
    def _container_name_from_dir(project_dir: str) -> str:
        """Resolve the deterministic container name from wasmdock.yml."""
        path = Path(project_dir).resolve()
        config = load_project_config(path)
        if not config:
            raise FileNotFoundError(f"No wasmdock.yml found in {path}")
        return f"wasmdock-{config['name']}"

    def logs(self, container_id: str, tail: int = 100) -> str:
        """Retrieve recent logs from a container."""
        try:
            container = self._client.containers.get(container_id)
            raw: bytes = container.logs(tail=tail)
            return raw.decode("utf-8", errors="replace")
        except DockerException as exc:
            return f"Error retrieving logs: {exc}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_existing(self, name: str) -> None:
        """Remove a container by name if it already exists (best effort)."""
        try:
            existing = self._client.containers.get(name)
        except DockerException:
            return
        try:
            existing.remove(force=True)
            console.print(f"[dim]Replaced existing container {name}[/dim]")
        except DockerException:
            pass

    @staticmethod
    def _format_ports(ports: dict | None) -> str:
        """Render Docker's port mapping dict as a compact host->container string."""
        if not ports:
            return ""
        parts: list[str] = []
        for container_port, bindings in ports.items():
            if bindings:
                host = bindings[0].get("HostPort", "")
                parts.append(f"{host}->{container_port}")
            else:
                parts.append(container_port)
        return ", ".join(parts)

    def _wait_for_ready(self, container_id: str) -> None:
        """Poll container status until it is running or timeout expires."""
        deadline = time.monotonic() + _READINESS_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                container = self._client.containers.get(container_id)
                status = container.status
                if status == "running":
                    return
                if status in ("exited", "dead"):
                    console.print(f"[yellow]Container exited with status: {status}[/yellow]")
                    return
            except DockerException:
                pass
            time.sleep(_READINESS_POLL_INTERVAL)

        console.print("[yellow]Container readiness check timed out[/yellow]")

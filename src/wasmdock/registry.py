"""OCI registry operations for WASM images."""

from __future__ import annotations

import docker
from docker.errors import DockerException
from rich.console import Console

console = Console()


class Registry:
    """Push and pull WASM container images to/from OCI-compliant registries."""

    def __init__(self) -> None:
        self._client = docker.from_env()

    def push(self, image_name: str, target: str) -> None:
        """Tag and push a local WASM image to a remote registry.

        Args:
            image_name: Local image name (e.g. ``wasmdock-myapp:latest``).
            target: Full remote reference
                    (e.g. ``ghcr.io/user/myapp:latest``).
        """
        try:
            image = self._client.images.get(image_name)
            repo, _, tag = target.rpartition(":")
            if not repo:
                repo = target
                tag = "latest"

            image.tag(repo, tag=tag)
            console.print(f"Pushing {target}...")

            output = self._client.images.push(repo, tag=tag, stream=True, decode=True)
            for line in output:
                if "error" in line:
                    raise DockerException(line["error"])
                status = line.get("status", "")
                if status:
                    console.print(f"  {status}")

            console.print(f"[green]Pushed {target}[/green]")

        except DockerException as exc:
            console.print(f"[red]Push failed: {exc}[/red]")
            raise

    def pull(self, image_name: str) -> None:
        """Pull a WASM image from a remote OCI registry.

        Args:
            image_name: Full image reference
                        (e.g. ``ghcr.io/user/myapp:latest``).
        """
        try:
            console.print(f"Pulling {image_name}...")
            self._client.images.pull(image_name, platform="wasi/wasm")
            console.print(f"[green]Pulled {image_name}[/green]")
        except DockerException as exc:
            console.print(f"[red]Pull failed: {exc}[/red]")
            raise

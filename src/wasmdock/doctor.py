"""Environment diagnostics for the Docker WASM toolchain.

``wasmdock doctor`` inspects the local Docker installation and reports
whether it is ready to build and run WebAssembly containers. The most
common cause of confusing failures is an environment that has not enabled
Docker's WASM support, so surfacing these checks up front saves users a
lot of debugging.
"""

from __future__ import annotations

from dataclasses import dataclass

import docker
from docker.errors import DockerException
from rich.console import Console
from rich.table import Table

from wasmdock.models import WasmRuntime

console = Console()


@dataclass
class Check:
    """A single environment check result."""

    name: str
    passed: bool
    detail: str
    required: bool = True


class Doctor:
    """Inspects the Docker environment for WASM-container readiness."""

    def run_checks(self) -> list[Check]:
        """Run every diagnostic and return the results."""
        try:
            client = docker.from_env()
        except DockerException as exc:
            return [
                Check(
                    name="Docker client",
                    passed=False,
                    detail=f"Could not create Docker client: {exc}",
                )
            ]

        checks: list[Check] = []
        info = self._safe_info(client)

        checks.append(self._check_daemon(info))
        if info is None:
            return checks

        checks.append(self._check_containerd_store(info))
        checks.append(self._check_wasm_shims(info))
        return checks

    def report(self) -> bool:
        """Print a Rich report and return True if all required checks pass."""
        checks = self.run_checks()

        table = Table(title="WasmDock Doctor", show_lines=True)
        table.add_column("Check", style="bold")
        table.add_column("Status", justify="center")
        table.add_column("Detail")

        for check in checks:
            if check.passed:
                status = "[green]PASS[/green]"
            elif check.required:
                status = "[red]FAIL[/red]"
            else:
                status = "[yellow]WARN[/yellow]"
            table.add_row(check.name, status, check.detail)

        console.print(table)

        ok = all(c.passed for c in checks if c.required)
        if ok:
            console.print("[green]Environment looks ready for WASM containers.[/green]")
        else:
            console.print(
                "[red]Environment is not ready.[/red] "
                "See https://docs.docker.com/desktop/wasm/ to enable WASM support."
            )
        return ok

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_info(client: docker.DockerClient) -> dict | None:
        """Return ``docker info`` output, or None if the daemon is unreachable."""
        try:
            client.ping()
            return dict(client.info())
        except DockerException:
            return None

    @staticmethod
    def _check_daemon(info: dict | None) -> Check:
        if info is None:
            return Check(
                name="Docker daemon",
                passed=False,
                detail="Docker daemon is not reachable. Is Docker Desktop running?",
            )
        version = info.get("ServerVersion", "unknown")
        return Check(
            name="Docker daemon",
            passed=True,
            detail=f"Reachable (Server {version})",
        )

    @staticmethod
    def _check_containerd_store(info: dict) -> Check:
        """containerd image store is required for the WASM runtime shims."""
        drivers = info.get("DriverStatus") or []
        driver = info.get("Driver", "")
        uses_containerd = driver == "overlayfs" or any(
            "io.containerd" in str(row) for row in drivers
        )
        return Check(
            name="containerd image store",
            passed=uses_containerd,
            detail=(
                f"Storage driver: {driver or 'unknown'}"
                if uses_containerd
                else "Enable 'Use containerd for pulling and storing images' in Docker settings"
            ),
        )

    @staticmethod
    def _check_wasm_shims(info: dict) -> Check:
        """Detect installed WASM runtime shims from the daemon's runtimes."""
        runtimes = info.get("Runtimes") or {}
        known = {rt.containerd_runtime for rt in WasmRuntime}
        found = sorted(name for name in runtimes if name in known)
        return Check(
            name="WASM runtime shims",
            passed=bool(found),
            detail=(
                f"Found: {', '.join(found)}"
                if found
                else "No WASM shims detected (wasmtime/spin/wasmedge/slight)"
            ),
            required=False,
        )

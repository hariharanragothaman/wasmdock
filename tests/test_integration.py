"""End-to-end integration tests that exercise a real Docker daemon.

These are **opt-in** and excluded from the default test run. Run them with:

    pytest -m integration

They require Docker with WebAssembly support (Docker Desktop 4.15+ with the
containerd image store and WASM enabled). When Docker is unreachable the suite
is skipped; when Docker is present but cannot build/run WASM, the affected test
skips rather than failing so the marker stays usable on plain Docker hosts.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import docker
import pytest
from docker.errors import DockerException

from wasmdock.builder import Builder
from wasmdock.models import WasmRuntime
from wasmdock.scaffolder import Scaffolder

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.integration


def _docker_available() -> bool:
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


requires_docker = pytest.mark.skipif(not _docker_available(), reason="Docker daemon not available")


@requires_docker
class TestEndToEnd:
    def test_scaffold_build_and_run_data_processor(self, tmp_path: Path) -> None:
        project = Scaffolder().scaffold(
            name="itest-proc",
            runtime=WasmRuntime.WASMTIME,
            language="rust",
            template="data-processor",
            output_dir=str(tmp_path),
        )

        builder = Builder()
        result = builder.build(project)
        if not result.success:
            pytest.skip(f"WASM build not supported on this host: {result.errors}")

        assert result.image_name == project.image_name
        assert result.image_size_mb >= 0

        try:
            output = builder._client.containers.run(
                result.image_name,
                platform="wasi/wasm",
                runtime=WasmRuntime.WASMTIME.containerd_runtime,
                remove=True,
            )
        except DockerException as exc:
            pytest.skip(f"WASM runtime not available on this host: {exc}")
        else:
            # The module runs to completion under the wasmtime shim; with no
            # stdin it simply produces no transformed lines on stdout.
            assert isinstance(output, (bytes, bytearray))
        finally:
            with contextlib.suppress(DockerException):
                builder._client.images.remove(result.image_name, force=True)

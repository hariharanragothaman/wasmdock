"""Tests for the WasmDock builder (mocked Docker interactions)."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from wasmdock.builder import Builder
from wasmdock.models import WasmProject, WasmRuntime


@pytest.fixture
def builder() -> Builder:
    with patch("wasmdock.builder.docker") as mock_docker:
        mock_docker.from_env.return_value = MagicMock()
        b = Builder()
    return b


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["docker", "build"], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.fixture
def sample_project(tmp_path: Path) -> WasmProject:
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    (project_dir / "Dockerfile").write_text("FROM scratch\n")
    return WasmProject(
        name="test-project",
        runtime=WasmRuntime.WASMTIME,
        language="rust",
        template="http-server-wasmtime",
        project_dir=project_dir,
    )


class TestBuildSuccess:
    def test_build_returns_success(self, builder: Builder, sample_project: WasmProject) -> None:
        with (
            patch("wasmdock.builder.subprocess.run", return_value=_completed(0)),
            patch.object(builder, "get_image_size", return_value=2.0),
        ):
            result = builder.build(sample_project)

        assert result.success is True
        assert result.image_name == "wasmdock-test-project:latest"
        assert result.image_size_mb == 2.0
        assert result.build_time_seconds >= 0
        assert result.errors == []

    def test_build_invokes_buildkit_with_correct_args(
        self, builder: Builder, sample_project: WasmProject
    ) -> None:
        with (
            patch("wasmdock.builder.subprocess.run", return_value=_completed(0)) as mock_run,
            patch.object(builder, "get_image_size", return_value=0.0),
        ):
            builder.build(sample_project)

        cmd = mock_run.call_args[0][0]
        env = mock_run.call_args[1]["env"]
        assert cmd[:2] == ["docker", "build"]
        assert "--platform" in cmd and cmd[cmd.index("--platform") + 1] == "wasi/wasm"
        assert "--tag" in cmd and cmd[cmd.index("--tag") + 1] == "wasmdock-test-project:latest"
        assert env["DOCKER_BUILDKIT"] == "1"


class TestBuildFailure:
    def test_build_failure_returns_errors(
        self, builder: Builder, sample_project: WasmProject
    ) -> None:
        with patch(
            "wasmdock.builder.subprocess.run",
            return_value=_completed(1, stderr="ERROR: rustc: unresolved import\n"),
        ):
            result = builder.build(sample_project)

        assert result.success is False
        assert any("unresolved import" in e for e in result.errors)

    def test_build_docker_cli_missing(self, builder: Builder, sample_project: WasmProject) -> None:
        with patch("wasmdock.builder.subprocess.run", side_effect=FileNotFoundError):
            result = builder.build(sample_project)

        assert result.success is False
        assert "docker CLI not found" in result.errors[0]

    def test_build_missing_dockerfile(self, builder: Builder, tmp_path: Path) -> None:
        project = WasmProject(
            name="no-docker",
            runtime=WasmRuntime.WASMTIME,
            language="rust",
            template="http-server-wasmtime",
            project_dir=tmp_path / "empty",
        )
        (tmp_path / "empty").mkdir()

        result = builder.build(project)

        assert result.success is False
        assert any("Dockerfile" in e for e in result.errors)

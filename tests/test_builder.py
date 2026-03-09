"""Tests for the WasmDock builder (mocked Docker interactions)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import BuildError, DockerException

from wasmdock.builder import Builder
from wasmdock.models import WasmProject, WasmRuntime


@pytest.fixture
def builder() -> Builder:
    with patch("wasmdock.builder.docker") as mock_docker:
        mock_docker.from_env.return_value = MagicMock()
        b = Builder()
    return b


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
    def test_build_returns_success(
        self, builder: Builder, sample_project: WasmProject
    ) -> None:
        mock_image = MagicMock()
        mock_image.attrs = {"Size": 2 * 1024 * 1024}
        builder._client.images.build.return_value = (mock_image, [])

        result = builder.build(sample_project)

        assert result.success is True
        assert result.image_name == "wasmdock-test-project:latest"
        assert result.image_size_mb == 2.0
        assert result.build_time_seconds > 0
        assert result.errors == []

    def test_build_calls_docker_with_correct_platform(
        self, builder: Builder, sample_project: WasmProject
    ) -> None:
        mock_image = MagicMock()
        mock_image.attrs = {"Size": 0}
        builder._client.images.build.return_value = (mock_image, [])

        builder.build(sample_project)

        builder._client.images.build.assert_called_once()
        call_kwargs = builder._client.images.build.call_args[1]
        assert call_kwargs["platform"] == "wasi/wasm"
        assert call_kwargs["tag"] == "wasmdock-test-project:latest"


class TestBuildFailure:
    def test_build_failure_returns_errors(
        self, builder: Builder, sample_project: WasmProject
    ) -> None:
        builder._client.images.build.side_effect = BuildError(
            reason="compilation failed",
            build_log=[{"error": "rustc: unresolved import"}],
        )

        result = builder.build(sample_project)

        assert result.success is False
        assert len(result.errors) > 0

    def test_build_docker_exception(
        self, builder: Builder, sample_project: WasmProject
    ) -> None:
        builder._client.images.build.side_effect = DockerException(
            "Docker daemon not running"
        )

        result = builder.build(sample_project)

        assert result.success is False
        assert "Docker daemon not running" in result.errors[0]

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

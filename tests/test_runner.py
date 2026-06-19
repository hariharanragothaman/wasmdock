"""Tests for the WasmDock container runner (mocked Docker interactions)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from docker.errors import DockerException

from wasmdock.models import WasmProject, WasmRuntime
from wasmdock.runner import Runner


@pytest.fixture
def runner() -> Runner:
    with patch("wasmdock.runner.docker") as mock_docker:
        mock_docker.from_env.return_value = MagicMock()
        return Runner()


@pytest.fixture
def project() -> WasmProject:
    return WasmProject(
        name="demo",
        runtime=WasmRuntime.WASMTIME,
        language="rust",
        template="http-server-wasmtime",
        project_dir=MagicMock(),
    )


class TestRun:
    def test_run_passes_wasm_platform_and_runtime(
        self, runner: Runner, project: WasmProject
    ) -> None:
        container = MagicMock()
        container.id = "deadbeefcafe"
        runner._client.containers.run.return_value = container

        with patch.object(runner, "_wait_for_ready"), patch.object(runner, "_remove_existing"):
            result = runner.run(project, port=8080)

        kwargs = runner._client.containers.run.call_args[1]
        assert kwargs["platform"] == "wasi/wasm"
        assert kwargs["runtime"] == "io.containerd.wasmtime.v1"
        assert kwargs["name"] == "wasmdock-demo"
        assert result.container_id == "deadbeefcafe"
        assert result.port == 8080

    def test_run_is_idempotent_removes_prior_container(
        self, runner: Runner, project: WasmProject
    ) -> None:
        prior = MagicMock()
        new = MagicMock()
        new.id = "newid"
        # First get() (in _remove_existing) returns the prior container.
        runner._client.containers.get.return_value = prior
        runner._client.containers.run.return_value = new

        with patch.object(runner, "_wait_for_ready"):
            runner.run(project, port=8080)

        prior.remove.assert_called_once_with(force=True)

    def test_run_reraises_docker_error(self, runner: Runner, project: WasmProject) -> None:
        runner._client.containers.run.side_effect = DockerException("boom")
        with pytest.raises(DockerException):
            runner.run(project)


class TestStopLogs:
    def test_stop_stops_and_removes(self, runner: Runner) -> None:
        container = MagicMock()
        runner._client.containers.get.return_value = container

        runner.stop("abc123")

        container.stop.assert_called_once()
        container.remove.assert_called_once_with(force=True)

    def test_stop_swallows_docker_error(self, runner: Runner) -> None:
        runner._client.containers.get.side_effect = DockerException("gone")
        runner.stop("abc123")  # should not raise

    def test_logs_decodes_bytes(self, runner: Runner) -> None:
        container = MagicMock()
        container.logs.return_value = b"line one\nline two"
        runner._client.containers.get.return_value = container

        assert runner.logs("abc123", tail=10) == "line one\nline two"

    def test_logs_returns_error_string_on_failure(self, runner: Runner) -> None:
        runner._client.containers.get.side_effect = DockerException("nope")
        assert "Error retrieving logs" in runner.logs("abc123")


class TestFromDir:
    def test_run_from_dir_missing_config_raises(self, runner: Runner) -> None:
        with (
            patch("wasmdock.runner.load_project_config", return_value={}),
            pytest.raises(FileNotFoundError),
        ):
            runner.run_from_dir("/tmp/missing")


class TestPsClean:
    def test_list_containers_maps_fields(self, runner: Runner) -> None:
        c = MagicMock()
        c.name = "wasmdock-demo"
        c.status = "running"
        c.image.tags = ["wasmdock-demo:latest"]
        c.ports = {"8080/tcp": [{"HostPort": "8080"}]}
        runner._client.containers.list.return_value = [c]

        rows = runner.list_containers()

        assert rows[0]["name"] == "wasmdock-demo"
        assert rows[0]["status"] == "running"
        assert rows[0]["image"] == "wasmdock-demo:latest"
        assert rows[0]["ports"] == "8080->8080/tcp"

    def test_clean_stops_and_optionally_removes_image(self, runner: Runner) -> None:
        with (
            patch(
                "wasmdock.runner.load_project_config",
                return_value={"name": "demo", "runtime": "wasmtime"},
            ),
            patch.object(runner, "stop") as mock_stop,
        ):
            runner.clean_from_dir("/tmp/proj", remove_image=True)

        mock_stop.assert_called_once_with("wasmdock-demo")
        runner._client.images.remove.assert_called_once_with("wasmdock-demo:latest", force=True)

    def test_clean_missing_config_raises(self, runner: Runner) -> None:
        with (
            patch("wasmdock.runner.load_project_config", return_value={}),
            pytest.raises(FileNotFoundError),
        ):
            runner.clean_from_dir("/tmp/missing")

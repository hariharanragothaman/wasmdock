"""Tests for the WasmDock CLI wiring (mocked subsystems)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

from wasmdock import __version__
from wasmdock.cli import app

runner = CliRunner()


class TestMetaCommands:
    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_templates_lists_all(self) -> None:
        result = runner.invoke(app, ["templates"])
        assert result.exit_code == 0
        assert "http-server-wasmtime" in result.stdout

    def test_runtimes_lists_all(self) -> None:
        result = runner.invoke(app, ["runtimes"])
        assert result.exit_code == 0
        assert "wasmtime" in result.stdout

    def test_init_rejects_unknown_runtime(self) -> None:
        result = runner.invoke(app, ["init", "x", "--runtime", "nope"])
        assert result.exit_code == 1
        assert "Unknown runtime" in result.stdout

    def test_init_rejects_unknown_template(self) -> None:
        result = runner.invoke(app, ["init", "x", "--template", "nope"])
        assert result.exit_code == 1
        assert "Unknown template" in result.stdout

    def test_init_infers_runtime_from_template(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["init", "spinapp", "--template", "http-server-spin", "-o", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert (tmp_path / "spinapp" / "wasmdock.yml").read_text().find("spin") != -1

    def test_init_infers_go_language_from_template(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["init", "goapp", "--template", "data-processor-go", "-o", str(tmp_path)]
        )
        assert result.exit_code == 0
        config = (tmp_path / "goapp" / "wasmdock.yml").read_text()
        assert "language: go" in config
        assert "runtime: wasmtime" in config

    def test_init_rejects_incompatible_runtime(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "init",
                "x",
                "--template",
                "http-server-spin",
                "--runtime",
                "wasmtime",
                "-o",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
        assert "targets the 'spin' runtime" in result.stdout


class TestPull:
    def test_pull_invokes_registry(self) -> None:
        with patch("wasmdock.registry.Registry") as mock_registry_cls:
            instance = mock_registry_cls.return_value
            result = runner.invoke(app, ["pull", "ghcr.io/u/app:latest"])
        assert result.exit_code == 0
        instance.pull.assert_called_once_with("ghcr.io/u/app:latest")


class TestStopLogs:
    def test_stop_invokes_runner(self) -> None:
        with patch("wasmdock.runner.Runner") as mock_runner_cls:
            instance = mock_runner_cls.return_value
            result = runner.invoke(app, ["stop", "-d", "/tmp/proj"])
        assert result.exit_code == 0
        instance.stop_from_dir.assert_called_once_with("/tmp/proj")

    def test_stop_missing_config_exits_nonzero(self) -> None:
        with patch("wasmdock.runner.Runner") as mock_runner_cls:
            instance = mock_runner_cls.return_value
            instance.stop_from_dir.side_effect = FileNotFoundError("no wasmdock.yml")
            result = runner.invoke(app, ["stop"])
        assert result.exit_code == 1

    def test_logs_invokes_runner(self) -> None:
        with patch("wasmdock.runner.Runner") as mock_runner_cls:
            instance = mock_runner_cls.return_value
            instance.logs_from_dir.return_value = "hello logs"
            result = runner.invoke(app, ["logs", "-n", "10"])
        assert result.exit_code == 0
        assert "hello logs" in result.stdout


class TestPsClean:
    def test_ps_empty(self) -> None:
        with patch("wasmdock.runner.Runner") as mock_runner_cls:
            mock_runner_cls.return_value.list_containers.return_value = []
            result = runner.invoke(app, ["ps"])
        assert result.exit_code == 0
        assert "No WasmDock containers" in result.stdout

    def test_ps_lists_rows(self) -> None:
        with patch("wasmdock.runner.Runner") as mock_runner_cls:
            mock_runner_cls.return_value.list_containers.return_value = [
                {
                    "name": "wasmdock-demo",
                    "status": "running",
                    "image": "wasmdock-demo:latest",
                    "ports": "8080->8080/tcp",
                }
            ]
            result = runner.invoke(app, ["ps"])
        assert result.exit_code == 0
        assert "wasmdock-demo" in result.stdout

    def test_clean_invokes_runner(self) -> None:
        with patch("wasmdock.runner.Runner") as mock_runner_cls:
            instance = mock_runner_cls.return_value
            result = runner.invoke(app, ["clean", "--images", "-d", "/tmp/proj"])
        assert result.exit_code == 0
        instance.clean_from_dir.assert_called_once_with("/tmp/proj", remove_image=True)

    def test_clean_missing_config_exits_nonzero(self) -> None:
        with patch("wasmdock.runner.Runner") as mock_runner_cls:
            instance = mock_runner_cls.return_value
            instance.clean_from_dir.side_effect = FileNotFoundError("no wasmdock.yml")
            result = runner.invoke(app, ["clean"])
        assert result.exit_code == 1


class TestDoctorCommand:
    def test_doctor_passes(self) -> None:
        with patch("wasmdock.doctor.Doctor") as mock_doctor_cls:
            mock_doctor_cls.return_value.report.return_value = True
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

    def test_doctor_fails(self) -> None:
        with patch("wasmdock.doctor.Doctor") as mock_doctor_cls:
            mock_doctor_cls.return_value.report.return_value = False
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1


class TestRunnerDirHelpers:
    def test_stop_from_dir_resolves_container_name(self) -> None:
        from wasmdock.runner import Runner

        with patch("wasmdock.runner.docker") as mock_docker:
            mock_docker.from_env.return_value = MagicMock()
            r = Runner()
        with (
            patch(
                "wasmdock.runner.load_project_config",
                return_value={"name": "demo", "runtime": "wasmtime"},
            ),
            patch.object(r, "stop") as mock_stop,
        ):
            r.stop_from_dir("/tmp/proj")
        mock_stop.assert_called_once_with("wasmdock-demo")

    def test_logs_from_dir_resolves_container_name(self) -> None:
        from wasmdock.runner import Runner

        with patch("wasmdock.runner.docker") as mock_docker:
            mock_docker.from_env.return_value = MagicMock()
            r = Runner()
        with (
            patch(
                "wasmdock.runner.load_project_config",
                return_value={"name": "demo", "runtime": "wasmtime"},
            ),
            patch.object(r, "logs", return_value="x") as mock_logs,
        ):
            out = r.logs_from_dir("/tmp/proj", tail=5)
        mock_logs.assert_called_once_with("wasmdock-demo", tail=5)
        assert out == "x"

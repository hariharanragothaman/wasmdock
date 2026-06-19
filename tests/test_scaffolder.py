"""Tests for the WasmDock scaffolder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from wasmdock.models import WasmRuntime
from wasmdock.scaffolder import Scaffolder


@pytest.fixture
def scaffolder() -> Scaffolder:
    return Scaffolder()


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path / "projects"


class TestScaffold:
    def test_scaffold_creates_project_dir(self, scaffolder: Scaffolder, tmp_output: Path) -> None:
        tmp_output.mkdir()
        project = scaffolder.scaffold(
            name="my-app",
            runtime=WasmRuntime.WASMTIME,
            template="http-server-wasmtime",
            output_dir=str(tmp_output),
        )
        assert project.project_dir.exists()
        assert project.project_dir.is_dir()
        assert project.name == "my-app"

    def test_scaffold_creates_dockerfile(self, scaffolder: Scaffolder, tmp_output: Path) -> None:
        tmp_output.mkdir()
        project = scaffolder.scaffold(
            name="dock-test",
            runtime=WasmRuntime.WASMTIME,
            template="http-server-wasmtime",
            output_dir=str(tmp_output),
        )
        dockerfile = project.project_dir / "Dockerfile"
        assert dockerfile.exists()
        content = dockerfile.read_text()
        assert "wasm32-wasip1" in content
        assert "scratch" in content

    def test_scaffold_creates_cargo_toml(self, scaffolder: Scaffolder, tmp_output: Path) -> None:
        tmp_output.mkdir()
        project = scaffolder.scaffold(
            name="cargo-test",
            runtime=WasmRuntime.WASMTIME,
            template="http-server-wasmtime",
            output_dir=str(tmp_output),
        )
        cargo = project.project_dir / "Cargo.toml"
        assert cargo.exists()
        content = cargo.read_text()
        assert "cargo_test" in content

    def test_scaffold_creates_source_files(self, scaffolder: Scaffolder, tmp_output: Path) -> None:
        tmp_output.mkdir()
        project = scaffolder.scaffold(
            name="src-test",
            runtime=WasmRuntime.WASMTIME,
            template="http-server-wasmtime",
            output_dir=str(tmp_output),
        )
        main_rs = project.project_dir / "src" / "main.rs"
        assert main_rs.exists()

    def test_scaffold_creates_wasmdock_yml(self, scaffolder: Scaffolder, tmp_output: Path) -> None:
        tmp_output.mkdir()
        project = scaffolder.scaffold(
            name="cfg-test",
            runtime=WasmRuntime.SPIN,
            template="http-server-spin",
            output_dir=str(tmp_output),
        )
        config_path = project.project_dir / "wasmdock.yml"
        assert config_path.exists()
        content = config_path.read_text()
        assert "spin" in content

    def test_scaffold_refuses_existing_directory(
        self, scaffolder: Scaffolder, tmp_output: Path
    ) -> None:
        tmp_output.mkdir()
        (tmp_output / "existing").mkdir()
        with pytest.raises(FileExistsError):
            scaffolder.scaffold(
                name="existing",
                runtime=WasmRuntime.WASMTIME,
                template="http-server-wasmtime",
                output_dir=str(tmp_output),
            )

    def test_scaffold_spin_template(self, scaffolder: Scaffolder, tmp_output: Path) -> None:
        tmp_output.mkdir()
        project = scaffolder.scaffold(
            name="spin-app",
            runtime=WasmRuntime.SPIN,
            template="http-server-spin",
            output_dir=str(tmp_output),
        )
        spin_toml = project.project_dir / "spin.toml"
        assert spin_toml.exists()
        lib_rs = project.project_dir / "src" / "lib.rs"
        assert lib_rs.exists()

    def test_scaffold_data_processor_template(
        self, scaffolder: Scaffolder, tmp_output: Path
    ) -> None:
        tmp_output.mkdir()
        project = scaffolder.scaffold(
            name="dp-app",
            runtime=WasmRuntime.WASMTIME,
            template="data-processor",
            output_dir=str(tmp_output),
        )
        main_rs = project.project_dir / "src" / "main.rs"
        assert main_rs.exists()
        content = main_rs.read_text()
        assert "InputRecord" in content


class TestListTemplates:
    def test_list_templates(self, scaffolder: Scaffolder) -> None:
        templates = scaffolder.list_templates()
        assert len(templates) >= 4
        names = [t["name"] for t in templates]
        assert "http-server-spin" in names
        assert "http-server-wasmtime" in names
        assert "data-processor" in names
        assert "edge-function" in names

    def test_template_has_required_fields(self, scaffolder: Scaffolder) -> None:
        for tmpl in scaffolder.list_templates():
            assert "name" in tmpl
            assert "description" in tmpl
            assert "runtime" in tmpl
            assert "language" in tmpl


class TestListRuntimes:
    def test_list_runtimes(self, scaffolder: Scaffolder) -> None:
        runtimes = scaffolder.list_runtimes()
        assert len(runtimes) == 4
        names = [r["name"] for r in runtimes]
        assert "wasmtime" in names
        assert "wasmedge" in names
        assert "spin" in names
        assert "slight" in names

    def test_runtime_has_containerd_string(self, scaffolder: Scaffolder) -> None:
        for rt in scaffolder.list_runtimes():
            assert rt["containerd_runtime"].startswith("io.containerd.")

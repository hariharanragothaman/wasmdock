"""Project scaffolding engine for WasmDock."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from wasmdock.config import save_project_config
from wasmdock.models import WasmProject, WasmRuntime
from wasmdock.templates import TEMPLATE_REGISTRY, get_template_dir

console = Console()


class Scaffolder:
    """Generates new WASM projects from Jinja2 templates."""

    def scaffold(
        self,
        name: str,
        runtime: WasmRuntime = WasmRuntime.WASMTIME,
        language: str = "rust",
        template: str = "http-server-wasmtime",
        output_dir: str = ".",
    ) -> WasmProject:
        """Scaffold a complete WASM project ready to build and run.

        Creates the project directory, renders all template files with
        project-specific values, and writes a ``wasmdock.yml`` config.
        """
        template_dir = get_template_dir(template)
        project_dir = Path(output_dir).resolve() / name

        if project_dir.exists():
            raise FileExistsError(f"Directory already exists: {project_dir}")

        project_dir.mkdir(parents=True)

        context = self._build_context(name, runtime, language, template)
        self._render_template_tree(template_dir, project_dir, context)

        save_project_config(
            project_dir,
            {
                "name": name,
                "runtime": runtime.value,
                "language": language,
                "template": template,
            },
        )

        project = WasmProject(
            name=name,
            runtime=runtime,
            language=language,
            template=template,
            project_dir=project_dir,
        )

        console.print(f"[green]Project scaffolded at {project_dir}[/green]")
        return project

    def list_templates(self) -> list[dict[str, str]]:
        """Return metadata for every available template."""
        return [
            {
                "name": name,
                "description": meta["description"],
                "runtime": meta["runtime"],
                "language": meta["language"],
            }
            for name, meta in TEMPLATE_REGISTRY.items()
        ]

    def list_runtimes(self) -> list[dict[str, str]]:
        """Return metadata for every supported WASM runtime."""
        return [
            {
                "name": rt.value,
                "display_name": rt.display_name,
                "containerd_runtime": rt.containerd_runtime,
                "description": rt.description,
            }
            for rt in WasmRuntime
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(
        name: str,
        runtime: WasmRuntime,
        language: str,
        template: str,
    ) -> dict[str, Any]:
        """Build the Jinja2 template context dictionary."""
        rust_target = "wasm32-wasip1"
        return {
            "project_name": name,
            "project_name_snake": name.replace("-", "_"),
            "runtime": runtime.value,
            "runtime_containerd": runtime.containerd_runtime,
            "language": language,
            "template": template,
            "rust_target": rust_target,
            "docker_platform": "wasi/wasm",
        }

    @staticmethod
    def _render_template_tree(
        template_dir: Path,
        dest_dir: Path,
        context: dict[str, Any],
    ) -> None:
        """Walk a template directory, rendering .j2 files in-place."""
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            keep_trailing_newline=True,
        )

        for src_path in sorted(template_dir.rglob("*")):
            if src_path.is_dir() or src_path.name == "__pycache__":
                continue

            rel = src_path.relative_to(template_dir)
            dest_path = dest_dir / rel

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.suffix == ".j2":
                dest_path = dest_path.with_suffix("")  # strip .j2
                tmpl = env.get_template(str(rel))
                rendered = tmpl.render(**context)
                dest_path.write_text(rendered)
            else:
                shutil.copy2(src_path, dest_path)

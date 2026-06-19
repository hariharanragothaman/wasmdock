"""WasmDock project configuration loading."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from pathlib import Path

_yaml = YAML()
_yaml.preserve_quotes = True

CONFIG_FILENAME = "wasmdock.yml"


def load_project_config(project_dir: Path) -> dict[str, Any]:
    """Load a project-level wasmdock.yml if it exists."""
    config_path = project_dir / CONFIG_FILENAME
    if not config_path.exists():
        return {}
    with config_path.open() as fh:
        data = _yaml.load(fh)
    return dict(data) if data else {}


def save_project_config(project_dir: Path, config: dict[str, Any]) -> Path:
    """Write project configuration to wasmdock.yml."""
    config_path = project_dir / CONFIG_FILENAME
    with config_path.open("w") as fh:
        _yaml.dump(config, fh)
    return config_path

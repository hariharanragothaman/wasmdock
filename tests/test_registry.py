"""Tests for the WasmDock OCI registry operations (mocked Docker)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from docker.errors import DockerException

from wasmdock.registry import Registry


@pytest.fixture
def registry() -> Registry:
    with patch("wasmdock.registry.docker") as mock_docker:
        mock_docker.from_env.return_value = MagicMock()
        return Registry()


class TestPush:
    def test_push_tags_and_pushes(self, registry: Registry) -> None:
        image = MagicMock()
        registry._client.images.get.return_value = image
        registry._client.images.push.return_value = [{"status": "Pushed"}]

        registry.push("wasmdock-app:latest", "ghcr.io/user/app:v1")

        image.tag.assert_called_once_with("ghcr.io/user/app", tag="v1")
        registry._client.images.push.assert_called_once()

    def test_push_defaults_tag_to_latest(self, registry: Registry) -> None:
        image = MagicMock()
        registry._client.images.get.return_value = image
        registry._client.images.push.return_value = []

        registry.push("wasmdock-app:latest", "ghcr.io/user/app")

        image.tag.assert_called_once_with("ghcr.io/user/app", tag="latest")

    def test_push_raises_on_stream_error(self, registry: Registry) -> None:
        registry._client.images.get.return_value = MagicMock()
        registry._client.images.push.return_value = [{"error": "denied"}]

        with pytest.raises(DockerException):
            registry.push("wasmdock-app:latest", "ghcr.io/user/app:v1")


class TestPull:
    def test_pull_uses_wasm_platform(self, registry: Registry) -> None:
        registry.pull("ghcr.io/user/app:latest")
        registry._client.images.pull.assert_called_once_with(
            "ghcr.io/user/app:latest", platform="wasi/wasm"
        )

    def test_pull_propagates_docker_error(self, registry: Registry) -> None:
        registry._client.images.pull.side_effect = DockerException("not found")
        with pytest.raises(DockerException):
            registry.pull("ghcr.io/user/missing:latest")

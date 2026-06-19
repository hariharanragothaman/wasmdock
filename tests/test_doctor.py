"""Tests for the WasmDock environment doctor (mocked Docker interactions)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from wasmdock.doctor import Doctor


def _make_doctor() -> Doctor:
    with patch("wasmdock.doctor.docker") as mock_docker:
        mock_docker.from_env.return_value = MagicMock()
        return Doctor()


class TestDoctor:
    def test_daemon_unreachable_fails(self) -> None:
        from docker.errors import DockerException

        doctor = _make_doctor()
        with patch("wasmdock.doctor.docker.from_env", side_effect=DockerException("no daemon")):
            checks = doctor.run_checks()

        assert len(checks) == 1
        assert checks[0].passed is False

    def test_healthy_environment_passes(self) -> None:
        doctor = _make_doctor()
        info = {
            "ServerVersion": "27.0.0",
            "Driver": "overlayfs",
            "DriverStatus": [],
            "Runtimes": {
                "runc": {},
                "io.containerd.wasmtime.v1": {},
                "io.containerd.spin.v2": {},
            },
        }
        client = MagicMock()
        client.info.return_value = info
        with patch("wasmdock.doctor.docker.from_env", return_value=client):
            checks = doctor.run_checks()

        by_name = {c.name: c for c in checks}
        assert by_name["Docker daemon"].passed is True
        assert by_name["containerd image store"].passed is True
        assert by_name["WASM runtime shims"].passed is True
        assert "io.containerd.wasmtime.v1" in by_name["WASM runtime shims"].detail

    def test_missing_wasm_shim_is_warning_not_required(self) -> None:
        doctor = _make_doctor()
        info = {
            "ServerVersion": "27.0.0",
            "Driver": "overlayfs",
            "DriverStatus": [],
            "Runtimes": {"runc": {}},
        }
        client = MagicMock()
        client.info.return_value = info
        with patch("wasmdock.doctor.docker.from_env", return_value=client):
            ok = doctor.report()

        # Shim check is non-required, so a healthy daemon + store still passes.
        assert ok is True

    def test_no_containerd_store_fails(self) -> None:
        doctor = _make_doctor()
        info = {
            "ServerVersion": "24.0.0",
            "Driver": "overlay2",
            "DriverStatus": [],
            "Runtimes": {"runc": {}},
        }
        client = MagicMock()
        client.info.return_value = info
        with patch("wasmdock.doctor.docker.from_env", return_value=client):
            ok = doctor.report()

        assert ok is False

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request

from typer.testing import CliRunner

import lexo.cli.app as cli_app
from lexo.update import UpdateCheckError, UpdateStatus, check_update_available

runner = CliRunner()


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def test_check_update_available_detects_newer_version() -> None:
    def opener(_request: Request, *, timeout: float) -> FakeResponse:
        assert timeout == 3.0
        return FakeResponse({"info": {"version": "0.2.0"}})

    status = check_update_available(current_version="0.1.0", opener=opener)

    assert status.update_available
    assert status.latest_version == "0.2.0"


def test_check_update_available_handles_current_version() -> None:
    def opener(_request: Request, *, timeout: float) -> FakeResponse:
        assert timeout == 3.0
        return FakeResponse({"info": {"version": "0.1.0"}})

    status = check_update_available(current_version="0.1.0", opener=opener)

    assert not status.update_available


def test_prerelease_sorts_before_final_release() -> None:
    def opener(_request: Request, *, timeout: float) -> FakeResponse:
        assert timeout == 3.0
        return FakeResponse({"info": {"version": "0.1.0"}})

    status = check_update_available(current_version="0.1.0a1", opener=opener)

    assert status.update_available


def test_check_update_available_wraps_network_errors() -> None:
    def opener(_request: Request, *, timeout: float) -> FakeResponse:
        assert timeout == 3.0
        raise URLError("offline")

    try:
        check_update_available(opener=opener)
    except UpdateCheckError as exc:
        assert "Could not check for updates" in str(exc)
    else:
        raise AssertionError("expected UpdateCheckError")


def test_cli_check_update(monkeypatch) -> None:
    def fake_check_update_available() -> UpdateStatus:
        return UpdateStatus(
            current_version="0.1.0",
            latest_version="0.2.0",
            update_available=True,
            package_url="https://pypi.org/project/lexo/",
        )

    monkeypatch.setattr(cli_app, "check_update_available", fake_check_update_available)

    result = runner.invoke(cli_app.app, ["check-update"])

    assert result.exit_code == 0
    assert "Update available" in result.stdout
    assert "0.2.0" in result.stdout

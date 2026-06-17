"""Check whether a newer Lexo release is available."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from packaging.version import InvalidVersion, Version

from lexo import __version__

PYPI_JSON_URL = "https://pypi.org/pypi/{package}/json"
PYPI_PROJECT_URL = "https://pypi.org/project/{package}/"
DEFAULT_PACKAGE_NAME = "lexo"


class UpdateCheckError(RuntimeError):
    """Raised when the update endpoint cannot be reached or parsed."""


class _Response(Protocol):
    def read(self) -> bytes: ...

    def __enter__(self) -> _Response: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class _UrlOpener(Protocol):
    def __call__(self, request: Request, *, timeout: float) -> _Response: ...


def _default_opener(request: Request, *, timeout: float) -> _Response:
    return urlopen(request, timeout=timeout)


@dataclass(frozen=True)
class UpdateStatus:
    current_version: str
    latest_version: str
    update_available: bool
    package_url: str


def check_update_available(
    *,
    package_name: str = DEFAULT_PACKAGE_NAME,
    current_version: str = __version__,
    timeout: float = 3.0,
    opener: _UrlOpener = _default_opener,
) -> UpdateStatus:
    """Fetch PyPI metadata and compare it with the installed version."""

    url = PYPI_JSON_URL.format(package=package_name)
    request = Request(url, headers={"User-Agent": f"lexo/{current_version}"})
    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, TypeError, ValueError) as exc:
        raise UpdateCheckError(f"Could not check for updates: {exc}") from exc

    latest_version = _latest_version(payload)
    return UpdateStatus(
        current_version=current_version,
        latest_version=latest_version,
        update_available=_is_newer(latest_version, current_version),
        package_url=PYPI_PROJECT_URL.format(package=package_name),
    )


def _latest_version(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise UpdateCheckError("Could not check for updates: invalid PyPI response")
    info = payload.get("info")
    if not isinstance(info, dict):
        raise UpdateCheckError("Could not check for updates: invalid PyPI response")
    version = info.get("version")
    if not isinstance(version, str) or not version:
        raise UpdateCheckError("Could not check for updates: missing latest version")
    return version


def _is_newer(candidate: str, current: str) -> bool:
    try:
        return Version(candidate) > Version(current)
    except InvalidVersion:
        return False

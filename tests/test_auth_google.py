from __future__ import annotations

import pytest
from google.auth.exceptions import RefreshError

from lexo.infra import auth_google
from lexo.infra.auth_google import AuthError


class FakeCreds:
    def __init__(self, *, valid=False, expired=False, refresh_token=None, refresh_raises=False):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self._refresh_raises = refresh_raises
        self.refreshed = False

    def refresh(self, _request) -> None:
        if self._refresh_raises:
            raise RefreshError("invalid_grant: Token has been expired or revoked.")
        self.valid = True
        self.refreshed = True


def test_is_authenticated_false_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_google, "_load", lambda: None)
    assert auth_google.is_authenticated() is False


def test_is_authenticated_false_when_expired_and_unrefreshable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_google, "_load", lambda: FakeCreds(expired=True, refresh_token=None))
    assert auth_google.is_authenticated() is False


def test_is_authenticated_true_when_refreshable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_google, "_load", lambda: FakeCreds(expired=True, refresh_token="r"))
    assert auth_google.is_authenticated() is True


def test_get_credentials_raises_when_not_signed_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_google, "_load", lambda: None)
    with pytest.raises(AuthError, match="Not signed in"):
        auth_google.get_credentials(interactive=False)


def test_get_credentials_raises_when_refresh_revoked(monkeypatch: pytest.MonkeyPatch) -> None:
    creds = FakeCreds(expired=True, refresh_token="r", refresh_raises=True)
    monkeypatch.setattr(auth_google, "_load", lambda: creds)
    with pytest.raises(AuthError, match="expired"):
        auth_google.get_credentials(interactive=False)


def test_get_credentials_refreshes_and_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    creds = FakeCreds(expired=True, refresh_token="r")
    saved: list[object] = []
    monkeypatch.setattr(auth_google, "_load", lambda: creds)
    monkeypatch.setattr(auth_google, "_save", saved.append)
    assert auth_google.get_credentials(interactive=False) is creds
    assert creds.refreshed is True
    assert saved == [creds]

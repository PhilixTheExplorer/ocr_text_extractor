"""Google OAuth using the installed-app loopback flow.

The token lives in the OS keychain (via keyring), never a pickle file. Uses the
least-privilege drive.file scope, which is enough to upload, OCR-export, and
delete the app's own temporary files.

Needs an OAuth client file (credentials.json) from Google Cloud Console.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httplib2
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from lexo.infra import paths
from lexo.infra.token_keyring import KeyringTokenStore

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_TOKEN_KEY = "google-oauth-token"
_store = KeyringTokenStore()

_SIGN_IN = "Sign in to Google to continue (CLI: `lexo login`)."


class AuthError(RuntimeError):
    """Google sign-in is missing, expired, or revoked. The message is safe to
    show a user and tells them how to recover."""


def _find_credentials_file() -> Path:
    candidates: list[Path] = []
    env = os.environ.get("LEXO_GOOGLE_CREDENTIALS")
    if env:
        candidates.append(Path(env))
    candidates.append(paths.config_dir() / "credentials.json")
    candidates.append(Path.cwd() / "credentials.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Google OAuth client file not found. Download credentials.json from the "
        f"Google Cloud Console and place it in {paths.config_dir()} or the current "
        "directory, or set LEXO_GOOGLE_CREDENTIALS."
    )


def _load() -> Credentials | None:
    raw = _store.get(_TOKEN_KEY)
    if not raw:
        return None
    return Credentials.from_authorized_user_info(json.loads(raw), SCOPES)


def _save(creds: Credentials) -> None:
    _store.set(_TOKEN_KEY, creds.to_json())


def is_authenticated() -> bool:
    """Best-effort, offline check for a usable token. Detects a missing token or
    one that is expired with no way to refresh, without any network call; a token
    that has been revoked server-side can only be caught when actually used (see
    `get_credentials`)."""
    try:
        creds = _load()
    except Exception:
        return False
    if creds is None:
        return False
    return creds.valid or bool(creds.expired and creds.refresh_token)


def logout() -> None:
    _store.delete(_TOKEN_KEY)


def login() -> None:
    flow = InstalledAppFlow.from_client_secrets_file(str(_find_credentials_file()), SCOPES)
    creds = flow.run_local_server(port=0)
    _save(creds)


def get_credentials(*, interactive: bool = False) -> Credentials:
    creds = _load()
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            # The refresh token itself is expired or was revoked; a stored token
            # exists but is unusable.
            if not interactive:
                raise AuthError(f"Your Google sign-in has expired. {_SIGN_IN}") from exc
        else:
            _save(creds)
            return creds
    elif not interactive:
        raise AuthError(f"Not signed in to Google. {_SIGN_IN}")
    login()
    refreshed = _load()
    assert refreshed is not None
    return refreshed


def build_drive_service(creds: Credentials | None = None, *, timeout: float = 60.0) -> Any:
    creds = creds or get_credentials(interactive=False)
    http = AuthorizedHttp(creds, http=httplib2.Http(timeout=timeout))
    return build("drive", "v3", http=http)

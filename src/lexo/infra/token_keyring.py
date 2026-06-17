"""TokenStore backed by the OS keychain (keyring). Replaces v1's pickle tokens."""

from __future__ import annotations

import keyring


class KeyringTokenStore:
    def __init__(self, service: str = "lexo") -> None:
        self.service = service

    def get(self, key: str) -> str | None:
        return keyring.get_password(self.service, key)

    def set(self, key: str, value: str) -> None:
        keyring.set_password(self.service, key, value)

    def delete(self, key: str) -> None:
        try:
            keyring.delete_password(self.service, key)
        except Exception:
            pass

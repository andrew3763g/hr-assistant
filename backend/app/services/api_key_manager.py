from __future__ import annotations

import base64
import getpass
import json
import os
from pathlib import Path
from typing import Mapping, Optional, cast

from cryptography.fernet import Fernet, InvalidToken

DEFAULT_STORE_PATH = Path(__file__).resolve().parents[2] / "temp" / "api_keys.enc"

KeyStore = dict[str, str]


def _kdf(passphrase: str) -> bytes:
    # Simple deterministic KDF for demo purposes. Replace with PBKDF2/Argon2 + salt for production.
    key = base64.urlsafe_b64encode(passphrase.encode("utf-8").ljust(32, b"0")[:32])
    return key


def _ensure_store(payload: object) -> KeyStore:
    if not isinstance(payload, dict):
        return {}
    payload_dict = cast(dict[object, object], payload)
    store: KeyStore = {}
    for provider_key, value in payload_dict.items():
        if isinstance(provider_key, str) and isinstance(value, str):
            store[provider_key] = value
    return store


class APIKeyManager:
    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = Path(
            os.getenv("HR_API_KEY_STORE", store_path or DEFAULT_STORE_PATH)
        )

    def _load(self, passphrase: str) -> KeyStore:
        if not self.store_path.exists():
            return {}
        fernet = Fernet(_kdf(passphrase))
        decrypted = fernet.decrypt(self.store_path.read_bytes())
        return _ensure_store(json.loads(decrypted.decode("utf-8")))

    def _save(self, obj: Mapping[str, str], passphrase: str) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        fernet = Fernet(_kdf(passphrase))
        encrypted = fernet.encrypt(json.dumps(dict(obj)).encode("utf-8"))
        self.store_path.write_bytes(encrypted)

    def set(self, provider: str, key: str, passphrase: Optional[str] = None) -> None:
        pw = passphrase or getpass.getpass("Passphrase for encryption: ")
        data = self._load(pw)
        data[provider] = key
        self._save(data, pw)

    def get(self, provider: str, passphrase: Optional[str] = None) -> Optional[str]:
        if passphrase is None:
            pw = os.getenv("OPENAI_KEY_PASSPHRASE") or getpass.getpass(
                "Passphrase to unlock API keys: "
            )
        else:
            pw = passphrase
        try:
            data = self._load(pw)
            return data.get(provider)
        except (InvalidToken, ValueError):
            return None

    def configure_openai_key_interactive(self) -> None:
        key = input("Enter OpenAI API key (sk-...): ").strip()
        pw = getpass.getpass("Passphrase for encryption: ")
        self.set("openai", key, passphrase=pw)
        print(f"Key stored to: {self.store_path}")
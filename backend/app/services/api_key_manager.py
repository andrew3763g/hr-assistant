# backend/app/services/api_key_manager.py
from __future__ import annotations
import os, json, base64, getpass
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

# <-- добавь/поправь дефолтный путь к хранилищу
DEFAULT_STORE_PATH = Path(__file__).resolve().parents[2] / "temp" / "api_keys.enc"

def _kdf(passphrase: str) -> bytes:
    # простой KDF для demo (для прод — PBKDF2/Argon2 + salt)
    key = base64.urlsafe_b64encode(passphrase.encode("utf-8").ljust(32, b"0")[:32])
    return key

class APIKeyManager:
    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = Path(
            os.getenv("HR_API_KEY_STORE", store_path or DEFAULT_STORE_PATH)
        )

    def _load(self, passphrase: str) -> dict:
        if not self.store_path.exists():
            return {}
        f = Fernet(_kdf(passphrase))
        data = f.decrypt(self.store_path.read_bytes())
        return json.loads(data.decode("utf-8"))

    def _save(self, obj: dict, passphrase: str) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        f = Fernet(_kdf(passphrase))
        enc = f.encrypt(json.dumps(obj).encode("utf-8"))
        self.store_path.write_bytes(enc)

    def set(self, provider: str, key: str, passphrase: Optional[str] = None) -> None:
        pw = passphrase or getpass.getpass("Passphrase for encryption: ")
        data = self._load(pw)
        data[provider] = key
        self._save(data, pw)

    def get(self, provider: str, passphrase: Optional[str] = None) -> Optional[str]:
        if passphrase is None:
            # интерактивный запрос — чтобы можно было вызывать без ENV
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

    # удобный конфигуратор
    def configure_openai_key_interactive(self) -> None:
        key = input("Enter OpenAI API key (sk-...): ").strip()
        pw  = getpass.getpass("Passphrase for encryption: ")
        self.set("openai", key, passphrase=pw)
        print(f"Key stored to: {self.store_path}")

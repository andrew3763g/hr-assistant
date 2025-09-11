# backend/app/config.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    # .../backend
    return Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """
    Минимальный, но устойчивый к разным форматам конфиг.

    - STORAGE_BACKEND: 'local' | 'gdrive'
    - GOOGLE_SERVICE_ACCOUNT_FILE: путь к service account JSON (или None)
    - GOOGLE_DRIVE_FOLDERS_FILE: путь к JSON-конфигу папок (по умолчанию backend/app/data/gdrive_folders.json, если существует)
    - GOOGLE_DRIVE_FOLDERS: dict[str, str] — плоская карта ключ -> ID папки.
      При чтении поддерживается:
        * путь к JSON-файлу;
        * JSON-строка;
        * словарь вида {"folders": {"resumes": {"id":"..."}, ...}}
        * "pairs" строка вида "resumes:1AbC, vacancies:9XyZ"
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )
    # внутри класса Settings(BaseSettings)
    OPENAI_KEY_PASSPHRASE: str | None = Field(
        default=None,
        description="Пароль к зашифрованному хранилищу API-ключей",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",  # как у тебя
        extra="ignore",
        case_sensitive=False,
    )
    # --- БД ---
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://hruser:hrpassword@localhost:5432/hrdb",
        description="SQLAlchemy URL, например postgresql+psycopg://user:pass@host:5432/dbname",
    )
    DEBUG: bool = Field(default=False)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # если случайно указали "postgresql://" без драйвера — допишем psycopg
        if isinstance(v, str) and v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    STORAGE_BACKEND: str = Field(default="local")
    GOOGLE_SERVICE_ACCOUNT_FILE: Optional[Path] = Field(default=None)

    GOOGLE_DRIVE_FOLDERS_FILE: Optional[Path] = Field(default=None)
    GOOGLE_DRIVE_FOLDERS: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_gdrive_folders(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(data or {})
        base = _project_root()

        # 1) подставим дефолтный файл, если явно не задан
        if not data.get("GOOGLE_DRIVE_FOLDERS_FILE"):
            candidate = base / "app" / "data" / "gdrive_folders.json"
            if candidate.exists():
                data["GOOGLE_DRIVE_FOLDERS_FILE"] = candidate

        # утилита преобразования в "ключ -> id"
        def _flatten(obj: Any) -> Dict[str, str]:
            if isinstance(obj, dict) and "folders" in obj:
                obj = obj["folders"]
            if isinstance(obj, dict):
                out: Dict[str, str] = {}
                for k, v in obj.items():
                    if isinstance(v, dict) and "id" in v:
                        out[k] = str(v["id"])
                    else:
                        out[k] = str(v)
                return out
            return {}

        folders_val = data.get("GOOGLE_DRIVE_FOLDERS")

        # 2) приоритет: файл, если есть и словарь пуст
        file_path = data.get("GOOGLE_DRIVE_FOLDERS_FILE")
        if file_path and not folders_val:
            try:
                raw = json.loads(Path(file_path).read_text(encoding="utf-8"))
                data["GOOGLE_DRIVE_FOLDERS"] = _flatten(raw)
                return data
            except Exception:
                # молча продолжаем — ниже ещё варианты
                pass

        # 3) если пришла строка — это либо путь, либо JSON, либо "pairs"
        if isinstance(folders_val, str):
            p = Path(folders_val)
            if p.exists():
                try:
                    raw = json.loads(p.read_text(encoding="utf-8"))
                    data["GOOGLE_DRIVE_FOLDERS"] = _flatten(raw)
                    return data
                except Exception:
                    data["GOOGLE_DRIVE_FOLDERS"] = {}
            else:
                # попробуем JSON
                try:
                    raw = json.loads(folders_val)
                    data["GOOGLE_DRIVE_FOLDERS"] = _flatten(raw)
                    return data
                except Exception:
                    # и формат "resumes:abc, vacancies:def"
                    pairs = [s for s in (s.strip() for s in folders_val.split(",")) if ":" in s]
                    data["GOOGLE_DRIVE_FOLDERS"] = {
                        k.strip(): v.strip() for k, v in (pair.split(":", 1) for pair in pairs)
                    }
                    return data

        # 4) если уже словарь — просто выровняем
        if isinstance(folders_val, dict):
            data["GOOGLE_DRIVE_FOLDERS"] = _flatten(folders_val)

        return data


settings = Settings()

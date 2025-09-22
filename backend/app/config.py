# backend/app/config.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from typing_extensions import Annotated
from pydantic.functional_validators import BeforeValidator
from pydantic import model_validator


def _clean_str(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip().strip('"').strip("'").rstrip("\r")
    return s


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v or "").strip().strip('"').strip(
        "'").strip()  # срежем пробелы/кавычки/CR
    s = s.lower().rstrip("\r")
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off", ""}:
        return False
    # last resort — всё, что непустое, считаем True
    return bool(s)


def parse_cors_env(v) -> List[str]:
    import json
    if v is None or v == "":
        return ["*"]
    if isinstance(v, list):
        return v
    s = str(v).strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s)]
        except Exception:
            pass
    return [x.strip() for x in s.split(",") if x.strip()]


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

    # @model_validator(mode="before")
    # @classmethod
    # def strip_cr_from_all_str_fields(cls, data: dict):
    #     if isinstance(data, dict):
    #         return {k: (v.rstrip("\r") if isinstance(v, str) else v) for k, v in data.items()}
    #     return data
    
    # --- БД ---

    DB_HOST: Annotated[str, BeforeValidator(_clean_str)] = "localhost"
    DB_PORT: int = 5432
    DB_NAME: Annotated[str, BeforeValidator(_clean_str)] = "hrdb"
    DB_USER: Annotated[str, BeforeValidator(_clean_str)] = "hruser"
    DB_PASSWORD: Annotated[str, BeforeValidator(_clean_str)] = "hrpassword"

    # Если хочешь задать DSN одной переменной – можно, иначе соберём ниже
    DATABASE_URL: str | None = None

    # Флаг окружения (локально vs docker)
    RUN_IN_DOCKER: Annotated[bool, BeforeValidator(_to_bool)] = False

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        host = "hr_postgres" if self.RUN_IN_DOCKER else self.DB_HOST
        # отключаем SSL negotiation для локального postgres
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{host}:{self.DB_PORT}/{self.DB_NAME}?sslmode=disable"
        )

    DEBUG: Annotated[bool, BeforeValidator(_to_bool)] = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # если случайно указали "postgresql://" без драйвера — допишем psycopg
        if isinstance(v, str) and v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    EMAIL_USE_TLS: Annotated[bool, BeforeValidator(_to_bool)] = True

    STORAGE_BACKEND: str = Field(default="local")
    GOOGLE_SERVICE_ACCOUNT_FILE: Annotated[Path |
                                           None, BeforeValidator(_clean_str)] = None
    GOOGLE_DRIVE_FOLDERS_FILE: Annotated[Path |
                                         None, BeforeValidator(_clean_str)] = None
    GOOGLE_DRIVE_FOLDERS: Dict[str, str] = Field(default_factory=dict)

    FFMPEG_BIN: str = Field(default="ffmpeg")
    FFPROBE_BIN: str = Field(default="ffprobe")
    EXTRACT_WAV: int = Field(default=1)
    MEDIA_TIMESLICE_MS: int = Field(default=45000)
    MEDIA_MAX_CHUNKS: int = Field(default=80)
    MEDIA_UPLOAD_ROOT: str = Field(default="uploads")
    CORS_ALLOW_ORIGINS: Annotated[List[str] | str,
                                  BeforeValidator(parse_cors_env)] = ["*"]
    GD_BACKUPS_FOLDER_ID: str = Field(default="")
    ADMIN_TOKEN: str = Field(default="changeme")

    # @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    # @classmethod
    # def _normalize_cors_origins(cls, value: Any) -> Any:
    #     if value is None:
    #         return value
    #     if isinstance(value, str):
    #         stripped = value.strip()
    #         if not stripped:
    #             return []
    #         if stripped.startswith("["):
    #             try:
    #                 parsed = json.loads(stripped)
    #                 if isinstance(parsed, list):
    #                     return parsed
    #             except json.JSONDecodeError:
    #                 pass
    #         return [item.strip() for item in stripped.split(",") if item.strip()]
    #     return value

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
                    pairs = [s for s in (s.strip()
                                         for s in folders_val.split(",")) if ":" in s]
                    data["GOOGLE_DRIVE_FOLDERS"] = {
                        k.strip(): v.strip() for k, v in (pair.split(":", 1) for pair in pairs)
                    }
                    return data

        # 4) если уже словарь — просто выровняем
        if isinstance(folders_val, dict):
            data["GOOGLE_DRIVE_FOLDERS"] = _flatten(folders_val)

        return data


settings = Settings()

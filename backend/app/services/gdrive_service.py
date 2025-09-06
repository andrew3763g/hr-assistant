# backend/app/services/gdrive_service.py
from __future__ import annotations

"""
Единая фабрика хранилища файлов:
- LocalStorage — запись в backend/app/uploads/<folder_key>/
- GoogleDriveStorage — запись в папки Google Drive по ID из settings.GOOGLE_DRIVE_FOLDERS

Единый интерфейс:
    s = get_storage()
    file_id = s.upload(b"hello", "test.txt", "resumes")
    data = s.download(file_id)
    s.delete(file_id)
"""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource
    from googleapiclient.http import MediaIoBaseUpload as _GUpload, MediaIoBaseDownload as _GDownload

import io
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

from backend.app.config import settings

# ---------------------------------------------------------------------------
# Базовый интерфейс
# ---------------------------------------------------------------------------


class FileStorage:
    """Мини-интерфейс файлового хранилища."""

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        raise NotImplementedError

    def download(self, file_id: str) -> bytes:
        raise NotImplementedError

    def delete(self, file_id: str) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Local storage
# ---------------------------------------------------------------------------


class LocalStorage(FileStorage):
    """Простое файловое хранилище на диске проекта."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # .../backend/app/uploads
        default_dir = Path(__file__).resolve().parents[1] / "uploads"
        self.base_dir = Path(base_dir or default_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _folder_dir(self, folder_key: str) -> Path:
        d = self.base_dir / folder_key
        d.mkdir(parents=True, exist_ok=True)
        return d

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        ext = "".join(Path(filename).suffixes) or ".bin"
        name = f"{uuid.uuid4().hex}{ext}"
        dst = self._folder_dir(folder_key) / name
        with open(dst, "wb") as fh:
            fh.write(data)
        # В качестве ID возвращаем абсолютный путь (понятно и без БД)
        return str(dst)

    def download(self, file_id: str) -> bytes:
        # принимаем и «local:/abs/path», и «/abs/path»
        path_str = file_id[len("local:") :] if file_id.startswith("local:") else file_id
        p = Path(path_str)
        with open(p, "rb") as fh:
            return fh.read()

    def delete(self, file_id: str) -> None:
        path_str = file_id[len("local:") :] if file_id.startswith("local:") else file_id
        p = Path(path_str)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                # не считаем критичной ошибкой
                pass


# ---------------------------------------------------------------------------
# Google Drive storage
# ---------------------------------------------------------------------------


class GoogleDriveStorage(FileStorage):
    """Хранилище в Google Drive (через Service Account)."""

    def __init__(self) -> None:
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "Google Drive backend requires google-api-python-client & google-auth. "
                "Install them and provide GOOGLE_SERVICE_ACCOUNT_FILE."
            ) from e
        self._MediaIoBaseUpload: "_GUpload" = MediaIoBaseUpload
        self._MediaIoBaseDownload: "_GDownload" = MediaIoBaseDownload
        self._build = build
        self.service: "Resource" = self._build("drive", "v3", credentials=self.creds)

        sa_path = settings.GOOGLE_SERVICE_ACCOUNT_FILE
        if not sa_path:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_FILE is not set. "
                "Укажи путь к service_account.json в .env."
            )

        scopes = ["https://www.googleapis.com/auth/drive"]
        self.creds = Credentials.from_service_account_file(str(sa_path), scopes=scopes)
        self.service = self._build("drive", "v3", credentials=self.creds)

        # плоский dict: ключ -> ID папки
        self.folders = dict(getattr(settings, "GOOGLE_DRIVE_FOLDERS", {}) or {})

    # ---- helpers ----

    def _folder_id(self, folder_key: str) -> str:
        try:
            fid = self.folders[folder_key]
            # на всякий случай поддержим старый формат {"id": "..."}
            if isinstance(fid, dict) and "id" in fid:
                fid = fid["id"]
            return str(fid)
        except KeyError as e:
            raise KeyError(
                f"GDrive: для ключа '{folder_key}' не настроен ID папки. "
                f"Проверь settings.GOOGLE_DRIVE_FOLDERS / gdrive_folders.json."
            ) from e

    @staticmethod
    def _mime(filename: str) -> str:
        return mimetypes.guess_type(filename)[0] or "application/octet-stream"

    # ---- API ----

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        file_metadata = {"name": filename, "parents": [self._folder_id(folder_key)]}
        media = self._MediaIoBaseUpload(io.BytesIO(data), mimetype=self._mime(filename))
        created = (
            self.service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        )
        return created["id"]

    def download(self, file_id: str) -> bytes:
        req = self.service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = self._MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        return buf.getvalue()

    def delete(self, file_id: str) -> None:
        try:
            self.service.files().delete(fileId=file_id).execute()
        except Exception:
            # удаление считаем best-effort
            pass


# ---------------------------------------------------------------------------
# Фабрика
# ---------------------------------------------------------------------------


def get_storage() -> FileStorage:
    """
    Возвращает реализацию согласно settings.STORAGE_BACKEND.
    Значения:
      - "local"  (по умолчанию)
      - "gdrive"
    """
    backend = (getattr(settings, "STORAGE_BACKEND", None) or "local").lower()
    if backend == "gdrive":
        return GoogleDriveStorage()
    return LocalStorage()


# Небольшой self-test можно выполнить так:
#   from backend.app.services.gdrive_service import get_storage
#   s = get_storage()
#   fid = s.upload(b"hello", "test.txt", "resumes")
#   assert s.download(fid) == b"hello"
#   s.delete(fid)

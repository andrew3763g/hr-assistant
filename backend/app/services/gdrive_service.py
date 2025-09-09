
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.config import settings


class FileStorage:
    """Мини-интерфейс файлового хранилища."""

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:  # pragma: no cover - интерфейс
        raise NotImplementedError

    def download(self, file_id: str) -> bytes:  # pragma: no cover - интерфейс
        raise NotImplementedError

    def delete(self, file_id: str) -> None:  # pragma: no cover - интерфейс
        raise NotImplementedError

    def list_files(self, folder_key: str) -> List[Dict]:  # pragma: no cover - интерфейс
        raise NotImplementedError

    def find_by_name(self, name: str, folder_key: str = "resumes") -> Optional[str]:
        for f in self.list_files(folder_key):
            if f.get("name") == name:
                return f.get("id")
        return None


class LocalStorage(FileStorage):
    """Простое локальное хранилище в папке /uploads/{folder_key}."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or (Path(__file__).resolve().parents[2] / "uploads")
        self.root.mkdir(parents=True, exist_ok=True)

    def _folder(self, key: str) -> Path:
        p = self.root / key
        p.mkdir(parents=True, exist_ok=True)
        return p

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        p = self._folder(folder_key) / filename
        p.write_bytes(data)
        return str(p)

    def download(self, file_id: str) -> bytes:
        return Path(file_id).read_bytes()

    def delete(self, file_id: str) -> None:
        try:
            Path(file_id).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass

    def list_files(self, folder_key: str) -> List[Dict]:
        p = self._folder(folder_key)
        out: List[Dict] = []
        for fp in p.iterdir():
            if fp.is_file():
                out.append(
                    {
                        "id": str(fp),
                        "name": fp.name,
                        "mimeType": "application/octet-stream",
                        "size": fp.stat().st_size,
                    }
                )
        return out


class GoogleDriveStorage(FileStorage):
    """Хранилище в Google Drive через Service Account.
    Поддерживает скачивание *как бинарных файлов*, так и Google Docs/Sheets/Slides — экспорт в PDF.
    """

    def __init__(self) -> None:
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload  # noqa: F401  - ссылочные
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Google Drive backend requires google-api-python-client & google-auth. "
                "Install them and provide GOOGLE_SERVICE_ACCOUNT_FILE."
            ) from e

        scopes = ["https://www.googleapis.com/auth/drive"]
        sa_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE
        if not sa_file:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE is not set in settings/.env")

        self._Credentials = Credentials  # keep for typing
        self._MediaIoBaseDownload = MediaIoBaseDownload
        self._MediaIoBaseUpload = MediaIoBaseUpload

        creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # ---------- helpers ----------

    @staticmethod
    def _folders_map() -> Dict[str, Any]:
        """Возвращает словарь { key -> id/obj } из настроек, устойчиво к разным структурам."""
        cfg = settings.GOOGLE_DRIVE_FOLDERS
        # cfg может быть pydantic-моделью с полем folders
        folders = getattr(cfg, "folders", None)
        if folders is None and isinstance(cfg, dict):
            folders = cfg.get("folders", cfg)
        if folders is None:
            folders = cfg
        return folders or {}

    @classmethod
    def _folder_id(cls, key: str) -> str:
        m = cls._folders_map()
        item = m.get(key)
        if isinstance(item, dict):
            fid = item.get("id")
        else:
            fid = item
        if not fid or not isinstance(fid, str):
            raise KeyError(f"Folder key '{key}' is not configured in GOOGLE_DRIVE_FOLDERS")
        return fid

    # ---------- API ----------

    def list_files(self, folder_key: str) -> List[Dict]:
        folder_id = self._folder_id(folder_key)
        files: List[Dict] = []
        page_token: Optional[str] = None
        while True:
            resp = (
                self.service.files()  # type: ignore[attr-defined]
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id,name,mimeType,modifiedTime,size)",
                    pageToken=page_token,
                    pageSize=1000,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )
            files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return files

    def find_by_name(self, name: str, folder_key: str = "resumes") -> Optional[str]:
        folder_id = self._folder_id(folder_key)
        # Аккуратно экранируем одинарные кавычки
        safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
        resp = (
            self.service.files()  # type: ignore[attr-defined]
            .list(
                q=f"name = '{safe_name}' and '{folder_id}' in parents and trashed=false",
                fields="files(id,name)",
                pageSize=10,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        files = resp.get("files", [])
        if files:
            return files[0].get("id")
        return None

    def download(self, file_id: str) -> bytes:
        meta = (
            self.service.files()  # type: ignore[attr-defined]
            .get(fileId=file_id, fields="id,name,mimeType,size")
            .execute()
        )
        mime = meta.get("mimeType", "")
        buf = io.BytesIO()
        if mime.startswith("application/vnd.google-apps"):
            # Это «Google файл» — экспортируем в PDF
            export_mime = "application/pdf"
            request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)  # type: ignore[attr-defined]
        else:
            request = self.service.files().get_media(fileId=file_id)  # type: ignore[attr-defined]

        downloader = self._MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        folder_id = self._folder_id(folder_key)
        media = self._MediaIoBaseUpload(io.BytesIO(data), mimetype="application/octet-stream", resumable=True)
        file_meta = {"name": filename, "parents": [folder_id]}
        resp = (
            self.service.files()  # type: ignore[attr-defined]
            .create(body=file_meta, media_body=media, fields="id")
            .execute()
        )
        return resp["id"]

    def delete(self, file_id: str) -> None:
        try:
            self.service.files().delete(fileId=file_id).execute()  # type: ignore[attr-defined]
        except Exception:
            pass


def get_storage() -> FileStorage:
    backend = (settings.STORAGE_BACKEND or "local").strip().lower()
    if backend == "gdrive":
        return GoogleDriveStorage()
    return LocalStorage()

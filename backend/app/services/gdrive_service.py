from __future__ import annotations

import importlib
import io
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Protocol, TypedDict, cast

from backend.app.config import settings


class FileMetadata(TypedDict, total=False):
    id: str
    name: str
    mimeType: str
    size: int
    modifiedTime: str


class FileStorage(Protocol):
    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        ...

    def download(self, file_id: str) -> bytes:
        ...

    def delete(self, file_id: str) -> None:
        ...

    def list_files(self, folder_key: str) -> List[FileMetadata]:
        ...

    def find_by_name(self, name: str, folder_key: str = "resumes") -> Optional[str]:
        ...


class LocalStorage:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or (Path(__file__).resolve().parents[2] / "uploads")
        self.root.mkdir(parents=True, exist_ok=True)

    def _folder(self, key: str) -> Path:
        folder = self.root / key
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        path = self._folder(folder_key) / filename
        path.write_bytes(data)
        return str(path)

    def download(self, file_id: str) -> bytes:
        return Path(file_id).read_bytes()

    def delete(self, file_id: str) -> None:
        try:
            Path(file_id).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass

    def list_files(self, folder_key: str) -> List[FileMetadata]:
        folder = self._folder(folder_key)
        items: List[FileMetadata] = []
        for path in folder.iterdir():
            if path.is_file():
                stat = path.stat()
                items.append(
                    {
                        "id": str(path),
                        "name": path.name,
                        "mimeType": "application/octet-stream",
                        "size": stat.st_size,
                    }
                )
        return items

    def find_by_name(self, name: str, folder_key: str = "resumes") -> Optional[str]:
        for metadata in self.list_files(folder_key):
            if metadata.get("name") == name:
                return metadata.get("id")
        return None


def _coerce_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _extract_folder_id(candidate: object) -> Optional[str]:
    if isinstance(candidate, str):
        return candidate
    if isinstance(candidate, Mapping):
        mapping_candidate = cast(Mapping[str, object], candidate)
        raw_value = mapping_candidate.get("id")
        if isinstance(raw_value, str):
            return raw_value
    return None


class GoogleDriveStorage:
    def __init__(self) -> None:
        try:  # pragma: no cover - требует внешние зависимости
            credentials_module = importlib.import_module("google.oauth2.service_account")
            discovery_module = importlib.import_module("googleapiclient.discovery")
            http_module = importlib.import_module("googleapiclient.http")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Google Drive backend requires google-api-python-client & google-auth. "
                "Install them and provide GOOGLE_SERVICE_ACCOUNT_FILE."
            ) from exc

        Credentials = getattr(credentials_module, "Credentials")
        MediaIoBaseDownload = getattr(http_module, "MediaIoBaseDownload")
        MediaIoBaseUpload = getattr(http_module, "MediaIoBaseUpload")
        build = getattr(discovery_module, "build")

        scopes = ["https://www.googleapis.com/auth/drive"]
        sa_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE
        if not sa_file:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE is not set in settings/.env")

        self._media_download_cls = MediaIoBaseDownload
        self._media_upload_cls = MediaIoBaseUpload

        creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    @staticmethod
    def _folders_map() -> Dict[str, object]:
        cfg = settings.GOOGLE_DRIVE_FOLDERS
        folders = getattr(cfg, "folders", None)
        if folders is None:
            try:
                folders = cfg.get("folders", cfg)  # type: ignore[call-arg]
            except AttributeError:
                folders = cfg
        return cast(Dict[str, object], folders or {})

    @classmethod
    def _folder_id(cls, key: str) -> str:
        mapping: Mapping[str, object] = cls._folders_map()
        folder_id = _extract_folder_id(mapping.get(key))
        if not folder_id:
            raise KeyError(f"Folder key '{key}' is not configured in GOOGLE_DRIVE_FOLDERS")
        return folder_id

    def list_files(self, folder_key: str) -> List[FileMetadata]:
        folder_id = self._folder_id(folder_key)
        files: List[FileMetadata] = []
        page_token: Optional[str] = None
        while True:
            resp = (
                self.service.files()  # type: ignore[no-untyped-call, attr-defined]
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
            files_payload = cast(Iterable[Mapping[str, object]], resp.get("files", []))
            for item in files_payload:
                files.append(
                    {
                        "id": cast(str, item.get("id", "")),
                        "name": cast(str, item.get("name", "")),
                        "mimeType": cast(str, item.get("mimeType", "")),
                        "size": _coerce_int(item.get("size", 0)),
                        "modifiedTime": cast(str, item.get("modifiedTime", "")),
                    }
                )
            page_token = cast(Optional[str], resp.get("nextPageToken"))
            if not page_token:
                break
        return files

    def find_by_name(self, name: str, folder_key: str = "resumes") -> Optional[str]:
        folder_id = self._folder_id(folder_key)
        safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
        resp = (
            self.service.files()  # type: ignore[no-untyped-call, attr-defined]
            .list(
                q=f"name = '{safe_name}' and '{folder_id}' in parents and trashed=false",
                fields="files(id,name)",
                pageSize=10,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        files = cast(List[Mapping[str, object]], resp.get("files", []))
        if files:
            file_id = files[0].get("id")
            return file_id if isinstance(file_id, str) else None
        return None

    def download(self, file_id: str) -> bytes:
        meta = (
            self.service.files()  # type: ignore[no-untyped-call, attr-defined]
            .get(fileId=file_id, fields="id,name,mimeType,size")
            .execute()
        )
        mime = cast(str, meta.get("mimeType", ""))
        buffer = io.BytesIO()
        if mime.startswith("application/vnd.google-apps"):
            request = self.service.files().export_media(  # type: ignore[no-untyped-call, attr-defined]
                fileId=file_id,
                mimeType="application/pdf",
            )
        else:
            request = self.service.files().get_media(fileId=file_id)  # type: ignore[no-untyped-call, attr-defined]

        downloader = self._media_download_cls(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        folder_id = self._folder_id(folder_key)
        media = self._media_upload_cls(io.BytesIO(data), mimetype="application/octet-stream", resumable=True)
        file_meta: Dict[str, object] = {"name": filename, "parents": [folder_id]}
        resp = (
            self.service.files()  # type: ignore[no-untyped-call, attr-defined]
            .create(body=file_meta, media_body=media, fields="id")
            .execute()
        )
        identifier = resp.get("id")
        if not isinstance(identifier, str):  # pragma: no cover - defensive
            raise RuntimeError("Google Drive did not return file id")
        return identifier

    def delete(self, file_id: str) -> None:
        try:
            self.service.files().delete(fileId=file_id).execute()  # type: ignore[no-untyped-call, attr-defined]
        except Exception:
            pass


def get_storage() -> FileStorage:
    backend = (settings.STORAGE_BACKEND or "local").strip().lower()
    if backend == "gdrive":
        return GoogleDriveStorage()
    return LocalStorage()

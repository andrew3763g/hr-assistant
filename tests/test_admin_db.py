import gzip
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import admin_db


class DummyStorage:
    def __init__(self):
        self.uploads: list[tuple[bytes, str, str]] = []
        self.downloads: dict[str, bytes] = {}

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        self.uploads.append((data, filename, folder_key))
        return "file-123"

    def download(self, file_id: str) -> bytes:
        try:
            return self.downloads[file_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise RuntimeError("unknown file") from exc


def _prepare_fake_pg_dump(monkeypatch, tmp_path, storage: DummyStorage):
    def fake_tmp_path(name: str) -> Path:
        return tmp_path / name

    def fake_run(cmd, check, stdout, stderr):  # noqa: ARG001
        for part in cmd:
            if part.startswith("--file="):
                dump_path = Path(part.split("=", 1)[1])
                dump_path.write_text("SQL DUMP", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(admin_db, "_tmp_path", fake_tmp_path)
    monkeypatch.setattr(admin_db.subprocess, "run", fake_run)
    monkeypatch.setattr(admin_db, "get_storage", lambda: storage)
    monkeypatch.setattr(admin_db.settings, "STORAGE_BACKEND", "gdrive")
    monkeypatch.setattr(admin_db, "_conn_uri_for_cli", lambda: "postgresql://user:pass@host/db")


@pytest.mark.asyncio
async def test_backup_database_success(tmp_path, monkeypatch):
    storage = DummyStorage()
    _prepare_fake_pg_dump(monkeypatch, tmp_path, storage)

    response = await admin_db.backup_db()

    assert response["file_id"] == "file-123"
    assert response["link"].startswith("https://drive.google.com")
    assert storage.uploads
    data, filename, folder_key = storage.uploads[0]
    assert filename.endswith(".sql.gz")
    assert folder_key == "BACKUPS"
    assert data.startswith(b"\x1f\x8b")  # gzip signature
    assert not any(tmp_path.rglob("*.sql"))
    assert not any(tmp_path.rglob("*.sql.gz"))


@pytest.mark.asyncio
async def test_backup_database_missing_pg_dump(tmp_path, monkeypatch):
    def fake_run(cmd, check, stdout, stderr):  # noqa: ARG001
        raise FileNotFoundError

    monkeypatch.setattr(admin_db.subprocess, "run", fake_run)
    monkeypatch.setattr(admin_db, "_tmp_path", lambda name: tmp_path / name)

    with pytest.raises(admin_db.HTTPException) as exc:
        await admin_db.backup_db()

    assert exc.value.status_code == 500
    assert "pg_dump" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_restore_database_success(tmp_path, monkeypatch):
    storage = DummyStorage()
    content = b"RESTORE SQL"
    storage.downloads["backup123"] = gzip.compress(content)

    def fake_tmp_path(name: str) -> Path:
        return tmp_path / name

    executed: list[list[str]] = []

    def fake_run(cmd, check, stdout, stderr):  # noqa: ARG001
        executed.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(admin_db, "_tmp_path", fake_tmp_path)
    monkeypatch.setattr(admin_db, "get_storage", lambda: storage)
    monkeypatch.setattr(admin_db.subprocess, "run", fake_run)
    monkeypatch.setattr(admin_db, "_conn_uri_for_cli", lambda: "postgresql://user:pass@host/db")

    result = await admin_db.restore_db({"file_id": "backup123"})

    assert result == {"ok": True}
    assert executed and executed[0][0] == "psql"
    assert not any(tmp_path.rglob("*.sql"))
    assert not any(tmp_path.rglob("*.sql.gz"))


@pytest.mark.asyncio
async def test_restore_database_requires_file_id():
    with pytest.raises(admin_db.HTTPException) as exc:
        await admin_db.restore_db({})

    assert exc.value.status_code == 400
    assert "file_id" in str(exc.value.detail)


def _admin_client(monkeypatch, tmp_path, storage):
    app = FastAPI()
    app.include_router(admin_db.router, prefix="/admin/db")
    client = TestClient(app)

    monkeypatch.setattr(admin_db.settings, "ADMIN_TOKEN", "secret-token")
    monkeypatch.setattr(admin_db, "_tmp_path", lambda name: tmp_path / name)
    monkeypatch.setattr(admin_db, "get_storage", lambda: storage)

    def fake_run(cmd, check, stdout, stderr):  # noqa: ARG001
        for part in cmd:
            if isinstance(part, str) and part.startswith("--file="):
                Path(part.split("=", 1)[1]).write_text("dump", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(admin_db.subprocess, "run", fake_run)
    monkeypatch.setattr(admin_db, "_conn_uri_for_cli", lambda: "postgresql://user:pass@host/db")
    return client


def test_admin_backup_requires_valid_token(tmp_path, monkeypatch):
    client = _admin_client(monkeypatch, tmp_path, DummyStorage())
    response = client.post("/admin/db/backup", headers={"X-Admin-Token": "wrong"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_admin_backup_storage_failure(tmp_path, monkeypatch):
    class FailingStorage(DummyStorage):
        def upload(self, data: bytes, filename: str, folder_key: str) -> str:  # noqa: ARG002
            raise KeyError("missing folder")

    client = _admin_client(monkeypatch, tmp_path, FailingStorage())

    response = client.post("/admin/db/backup", headers={"X-Admin-Token": "secret-token"})
    assert response.status_code == 500
    assert "BACKUPS" in response.json()["detail"]

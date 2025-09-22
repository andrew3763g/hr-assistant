from __future__ import annotations

"""Administrative database backup/restore endpoints."""

import gzip
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Annotated, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.app.config import settings
from backend.app.services.gdrive_service import get_storage


router = APIRouter(tags=["Admin"])  # <--- без prefix!

def check_admin_token(x_admin_token: str = Header(...)):
    from backend.app.config import settings
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

# def _admin_token_guard(token: Annotated[str | None, Header(alias="X-Admin-Token")]) -> None:
#     expected = (settings.ADMIN_TOKEN or "").strip()
#     if not expected or token != expected:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def _conn_uri_for_cli() -> str:
    conn = settings.db_url
    if conn.startswith("postgresql+"):
        conn = "postgresql" + conn[len("postgresql+"):]
    return conn


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _tmp_path(name: str) -> Path:
    return Path("/tmp") / name


def _gzip_file(source: Path, target: Path) -> None:
    with source.open("rb") as raw, gzip.open(target, "wb") as zipped:
        shutil.copyfileobj(raw, zipped)


def _gunzip_file(source: Path, target: Path) -> None:
    with gzip.open(source, "rb") as zipped, target.open("wb") as raw:
        shutil.copyfileobj(zipped, raw)


@router.post("/backup", dependencies=[Depends(check_admin_token)])
async def backup_db() -> Dict[str, str]:
    conn_uri = _conn_uri_for_cli()
    timestamp = _timestamp()
    sql_path = _tmp_path(f"hrdb_{timestamp}.sql")
    gz_path = sql_path.with_suffix(".sql.gz")

    dump_cmd = [
        "pg_dump",
        f"--dbname={conn_uri}",
        f"--file={sql_path}",
        "--clean",
        "--if-exists",
    ]

    try:
        subprocess.run(dump_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="pg_dump binary not found") from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=exc.stderr.decode("utf-8", errors="ignore")) from exc

    try:
        _gzip_file(sql_path, gz_path)
    finally:
        sql_path.unlink(missing_ok=True)

    storage = get_storage()
    data = gz_path.read_bytes()
    filename = gz_path.name

    try:
        file_id = storage.upload(data, filename, folder_key="BACKUPS")
    except KeyError as exc:
        raise HTTPException(status_code=500, detail="BACKUPS folder is not configured") from exc
    finally:
        gz_path.unlink(missing_ok=True)

    backend_kind = (getattr(settings, "STORAGE_BACKEND", "") or "").strip().lower()
    link = f"https://drive.google.com/file/d/{file_id}" if backend_kind == "gdrive" else file_id

    return {"file_id": file_id, "link": link}


@router.post("/restore", dependencies=[Depends(check_admin_token)])
async def restore_db(payload: Dict[str, str],) -> Dict[str, bool]:
    file_id = payload.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="file_id is required")

    storage = get_storage()

    gz_path = _tmp_path("restore.sql.gz")
    sql_path = _tmp_path("restore.sql")

    try:
        data = storage.download(file_id)
    except Exception as exc:  # pragma: no cover - storage backend varies
        raise HTTPException(status_code=500, detail=f"Failed to download backup: {exc}") from exc

    gz_path.write_bytes(data)

    try:
        _gunzip_file(gz_path, sql_path)
    finally:
        gz_path.unlink(missing_ok=True)

    conn_uri = _conn_uri_for_cli()
    restore_cmd = [
        "psql",
        f"--dbname={conn_uri}",
        f"--file={sql_path}",
    ]

    try:
        subprocess.run(restore_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="psql binary not found") from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=exc.stderr.decode("utf-8", errors="ignore")) from exc
    finally:
        sql_path.unlink(missing_ok=True)

    # NOTE: Restore operation overwrites existing schema with the backup contents.
    return {"ok": True}

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Literal, Mapping, Optional

from sqlalchemy.orm import Session

from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy, VacancyStatus

STORAGE = os.getenv("STORAGE_BACKEND", "local").lower()
ROOT = Path(__file__).resolve().parents[3]
INBOX_RESUMES = ROOT / "inbox" / "job_applications"
INBOX_VACANCIES = ROOT / "inbox" / "job_openings"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_docx(path: Path) -> str:
    try:
        from docx import Document  # type: ignore[import]

        return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    except Exception:
        return ""


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".txt":
        return _read_txt(path)
    if ext == ".docx":
        return _read_docx(path)
    if ext == ".pdf":
        return _read_pdf(path)
    return ""


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _split_name_from_filename(path: Path) -> tuple[str, str]:
    name = path.stem.replace("_", " ").replace("-", " ").strip()
    parts = [part for part in name.split() if part]
    if len(parts) >= 2:
        return parts[1], parts[0]
    return name, ""


def _find_email(text: str) -> Optional[str]:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def _ensure_dirs() -> None:
    INBOX_RESUMES.mkdir(parents=True, exist_ok=True)
    INBOX_VACANCIES.mkdir(parents=True, exist_ok=True)


ALLOWED_CANDIDATE_FIELDS = {
    "first_name",
    "last_name",
    "email",
    "resume_file_path",
    "original_text",
    "original_text_hash",
}

ALLOWED_VACANCY_FIELDS = {
    "title",
    "description",
    "status",
    "source_file_path",
    "original_text",
}


def _filter_allowed(data: Mapping[str, object | None], allowed: set[str]) -> dict[str, object]:
    return {key: value for key, value in data.items() if key in allowed and value is not None}


def _candidate_exists(db: Session, path: Path, text_hash: str) -> bool:
    if hasattr(Candidate, "original_text_hash"):
        return (
            db.query(Candidate)
            .filter(
                (Candidate.resume_file_path == str(path))
                | (Candidate.original_text_hash == text_hash)
            )
            .first()
            is not None
        )
    return (
        db.query(Candidate)
        .filter(Candidate.resume_file_path == str(path))
        .first()
        is not None
    )


def _vacancy_exists(db: Session, path: Path, text: str) -> bool:
    return (
        db.query(Vacancy)
        .filter((Vacancy.source_file_path == str(path)) | (Vacancy.original_text == text))
        .first()
        is not None
    )


def ingest_all(db: Session, kind: Literal["resumes", "vacancies"]) -> int:
    _ensure_dirs()

    if STORAGE == "gdrive":
        return 0

    folder = INBOX_RESUMES if kind == "resumes" else INBOX_VACANCIES
    exts: set[str] = {".txt", ".doc", ".docx", ".pdf"}
    files = [path for path in folder.glob("**/*") if path.is_file() and path.suffix.lower() in exts]

    imported = 0
    for path in files:
        text = _read_file(path)
        if not text.strip():
            continue

        text_hash = _hash_text(text)

        if kind == "resumes":
            if _candidate_exists(db, path, text_hash):
                continue

            first_name, last_name = _split_name_from_filename(path)
            email = _find_email(text)

            raw_payload: Mapping[str, object | None] = {
                "first_name": first_name or None,
                "last_name": last_name or None,
                "email": email,
                "resume_file_path": str(path),
                "original_text": text,
                "original_text_hash": text_hash if hasattr(Candidate, "original_text_hash") else None,
            }
            payload = _filter_allowed(raw_payload, ALLOWED_CANDIDATE_FIELDS)
            candidate = Candidate(**payload)  # type: ignore[arg-type]
            db.add(candidate)
        else:
            if _vacancy_exists(db, path, text):
                continue

            status_value: Optional[object]
            if hasattr(VacancyStatus, "open"):
                status_value = getattr(VacancyStatus, "open")
            else:
                status_value = None

            raw_payload = {
                "title": path.stem[:120],
                "description": text[:4000],
                "status": status_value,
                "source_file_path": str(path),
                "original_text": text,
            }
            payload = _filter_allowed(raw_payload, ALLOWED_VACANCY_FIELDS)
            vacancy = Vacancy(**payload)  # type: ignore[arg-type]
            db.add(vacancy)

        imported += 1

    if imported:
        db.commit()

    return imported

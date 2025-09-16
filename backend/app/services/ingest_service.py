# backend/app/services/ingest_service.py
from __future__ import annotations

import os
import re
import hashlib
from pathlib import Path
from typing import Literal, Tuple, Dict, Any

from sqlalchemy.orm import Session

from backend.app.models.candidate import Candidate  # модель с original_text (+ опц. original_text_hash)
from backend.app.models.vacancy import Vacancy, VacancyStatus

# --- Конфиг входных источников ------------------------------------------------

STORAGE = os.getenv("STORAGE_BACKEND", "local").lower()
ROOT = Path(__file__).resolve().parents[3]  # .../hr-assistant
INBOX_RESUMES = ROOT / "inbox" / "job_applications"
INBOX_VACANCIES = ROOT / "inbox" / "job_openings"

# --- Вспомогательные ----------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def _read_docx(path: Path) -> str:
    try:
        from docx import Document
        return "\n".join(p.text for p in Document(str(path)).paragraphs)
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
    # .doc можно пропустить / доп. обработчик, если хочется
    return ""

def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def _split_name_from_filename(path: Path) -> Tuple[str, str]:
    """Простейшая эвристика: 'Фамилия Имя ...' -> ('Имя','Фамилия')"""
    name = path.stem.replace("_", " ").replace("-", " ").strip()
    parts = [p for p in name.split() if p]
    if len(parts) >= 2:
        # допустим 'Иванов Иван' -> first='Иван', last='Иванов'
        return parts[1], parts[0]
    return name, ""  # first_name, last_name

def _find_email(text: str) -> str | None:
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None

def _ensure_dirs():
    INBOX_RESUMES.mkdir(parents=True, exist_ok=True)
    INBOX_VACANCIES.mkdir(parents=True, exist_ok=True)

# --- Allowed поля (фильтрация лишнего при создании ORM-объектов) ---------------

ALLOWED_CANDIDATE_FIELDS = {
    "first_name",
    "last_name",
    "email",
    "resume_file_path",
    "original_text",
    "original_text_hash",  # если колонка есть
}

ALLOWED_VACANCY_FIELDS = {
    "title",
    "description",
    "status",
    "source_file_path",
    "original_text",
}

def _filter_allowed(data: Dict[str, Any], allowed: set[str]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if k in allowed and v is not None}

# --- Основной импорт -----------------------------------------------------------

def ingest_all(db: Session, kind: Literal["resumes", "vacancies"]) -> int:
    """
    Импортирует все файлы из inbox/... (или из GDrive в перспективе).
    Возвращает количество добавленных записей.
    """
    _ensure_dirs()

    if STORAGE == "gdrive":
        # TODO: подключить текущий gdrive_service и скачать файлы во временную папку
        return 0  # заглушка, чтобы не ломать логику

    folder = INBOX_RESUMES if kind == "resumes" else INBOX_VACANCIES
    exts = {".txt", ".doc", ".docx", ".pdf"}
    files = [p for p in folder.glob("**/*") if p.is_file() and p.suffix.lower() in exts]

    imported = 0

    for path in files:
        text = _read_file(path)
        if not text.strip():
            continue

        text_hash = _hash_text(text)

        if kind == "resumes":
            # дедуп: по пути или по хэшу (если колонка есть)
            if hasattr(Candidate, "original_text_hash"):
                exists = db.query(Candidate).filter(
                    (Candidate.resume_file_path == str(path))
                    | (Candidate.original_text_hash == text_hash)
                ).first()
            else:
                exists = db.query(Candidate).filter(
                    Candidate.resume_file_path == str(path)
                ).first()

            if exists:
                continue

            first, last = _split_name_from_filename(path)
            email = _find_email(text)

            payload = {
                "first_name": first or None,
                "last_name": last or None,
                "email": email,
                "resume_file_path": str(path),
                "original_text": text,
                # добавим хэш, если колонка существует
                "original_text_hash": text_hash if hasattr(Candidate, "original_text_hash") else None,
            }

            payload = _filter_allowed(payload, ALLOWED_CANDIDATE_FIELDS)
            candidate = Candidate(**payload)
            db.add(candidate)
            imported += 1

        else:
            # вакансии: дубль по пути или по полностью одинаковому тексту
            exists = db.query(Vacancy).filter(
                (Vacancy.source_file_path == str(path)) | (Vacancy.original_text == text)
            ).first()
            if exists:
                continue

            payload = {
                "title": path.stem[:120],
                "description": text[:4000],  # защитимся от мегатекстов
                "status": VacancyStatus.open if hasattr(Vacancy, "status") else None,
                "source_file_path": str(path),
                "original_text": text,
                "location": "Unknown",
            }

            payload = _filter_allowed(payload, ALLOWED_VACANCY_FIELDS)
            vacancy = Vacancy(**payload)
            db.add(vacancy)
            imported += 1

    if imported:
        db.commit()

    return imported

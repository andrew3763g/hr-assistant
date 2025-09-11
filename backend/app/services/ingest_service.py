from __future__ import annotations
import os, re
from pathlib import Path
from typing import Iterable, Optional
from sqlalchemy.orm import Session
from docx import Document  # убедись, что в requirements есть python-docx

from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy

ROOT = Path(__file__).resolve().parents[3]
INBOX_RESUMES   = Path(os.getenv("INBOX_RESUMES",   ROOT / "inbox" / "job_applications"))
INBOX_VACANCIES = Path(os.getenv("INBOX_VACANCIES", ROOT / "inbox" / "job_openings"))
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)

def ingest_all(db: Session, kind: str) -> int:
    kind = kind.lower()
    if kind not in {"resumes", "vacancies"}:
        raise ValueError("kind must be 'resumes' or 'vacancies'")

    files = _iter_local_files(kind) if STORAGE_BACKEND == "local" else _iter_gdrive_files(kind)
    imported = 0

    if kind == "resumes":
        for f in files:
            data = _parse_resume_docx(f)
            if not data:
                continue
            if _candidate_exists(db, data):
                continue
            db.add(Candidate(**data))
            imported += 1
        db.commit()
        return imported

    # vacancies
    for f in files:
        data = _parse_vacancy_docx(f)
        if not data:
            continue
        if _vacancy_exists(db, data):
            continue
        db.add(Vacancy(**data))
        imported += 1
    db.commit()
    return imported

# ---------- источники ----------
def _iter_local_files(kind: str) -> Iterable[Path]:
    base = INBOX_RESUMES if kind == "resumes" else INBOX_VACANCIES
    base.mkdir(parents=True, exist_ok=True)
    for p in sorted(base.glob("*.docx")):
        if p.is_file():
            yield p

def _iter_gdrive_files(kind: str) -> Iterable[Path]:
    # Заглушка: сейчас работаем только локально.
    # Позже подключим backend.app.services.gdrive_service
    return _iter_local_files(kind)

# ---------- парсинг ----------
def _parse_resume_docx(path: Path) -> Optional[dict]:
    try:
        doc = Document(path)
        text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    except Exception:
        return None

    email = None
    m = EMAIL_RE.search(text)
    if m:
        email = m.group(0)

    # Имя и должность попробуем взять из имени файла: "Имя Фамилия - должность.docx"
    name_part = path.stem
    first_name = last_name = ""
    last_position = ""
    if " - " in name_part:
        name, last_position = name_part.split(" - ", 1)
    else:
        name = name_part
    parts = name.replace("_", " ").split()
    if parts:
        first_name = parts[0]
        if len(parts) > 1:
            last_name = " ".join(parts[1:])

    return {
        "first_name": first_name or None,
        "last_name": last_name or None,
        "email": email,
        "last_position": last_position or None,
        "last_company": None,
        "resume_file_path": str(path),
    }

def _parse_vacancy_docx(path: Path) -> Optional[dict]:
    try:
        doc = Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)
    except Exception:
        return None

    # Заголовок попытаемся взять из файла "Вакансия: <title>.docx" или первой строки
    title = path.stem
    if title.lower().startswith("вакансия:"):
        title = title.split(":", 1)[1].strip()
    elif paragraphs:
        title = paragraphs[0][:120]

    # Простая попытка вытащить город
    location = None
    for token in ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург"]:
        if token in text:
            location = token
            break

    return {
        "title": title,
        "location": location,
        "description": text,
        "status": "draft",
    }

# ---------- дедуп ----------
def _candidate_exists(db: Session, data: dict) -> bool:
    q = db.query(Candidate)
    if data.get("email"):
        q = q.filter(Candidate.email == data["email"])
    else:
        q = q.filter(
            Candidate.first_name == data.get("first_name"),
            Candidate.last_name  == data.get("last_name"),
            Candidate.last_position == data.get("last_position"),
        )
    return db.query(q.exists()).scalar()

def _vacancy_exists(db: Session, data: dict) -> bool:
    return db.query(db.query(Vacancy).filter(Vacancy.title == data["title"]).exists()).scalar()

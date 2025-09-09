
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Union, IO

from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document


def _normalize_text(text: str) -> str:
    # Приводим переносы и пробелы к норме
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\u00A0", " ").replace("\u202F", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.strip()
    return s


def _is_pdf_bytes(b: bytes) -> bool:
    return b[:4] == b"%PDF"


def _docx_text_from_bytes(b: bytes) -> str:
    doc = Document(io.BytesIO(b))
    parts = []
    for p in doc.paragraphs:
        if p.text:
            parts.append(p.text)
    for tbl in doc.tables:
        for row in tbl.rows:
            parts.append(" ".join(c.text for c in row.cells if c.text))
    return "\n".join(parts)


def extract_text(src: Union[str, Path, bytes, IO[bytes]], max_pages: int | None = None) -> str:
    """Достаёт текст из PDF/DOCX + нормализация.
    src: путь/bytes/IO[bytes]
    """
    data: bytes | None = None
    if isinstance(src, (str, Path)):
        path = Path(src)
        if path.suffix.lower() == ".docx":
            text = _docx_text_from_bytes(path.read_bytes())
            return _normalize_text(text)
        else:
            # считаем это PDF/прочее
            text = pdf_extract_text(str(path), maxpages=max_pages)
            return _normalize_text(text)

    # bytes/IO
    if hasattr(src, "read"):
        data = src.read()  # type: ignore[arg-type]
    elif isinstance(src, bytes):
        data = src
    else:
        raise TypeError("Unsupported src type")

    if _is_pdf_bytes(data):
        text = pdf_extract_text(io.BytesIO(data), maxpages=max_pages)
        return _normalize_text(text)
    else:
        # предполагаем DOCX
        text = _docx_text_from_bytes(data)
        return _normalize_text(text)


def parse_resume(src: Union[str, Path, bytes, IO[bytes]]) -> dict:
    """Мини-парсер резюме -> словарь для downstream-задач."""
    text = extract_text(src)

    # contacts
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"(?:\+?\d[\s\-()]{0,3}){7,}\d", text)

    # грубая детекция навыков по словам
    skill_words = [
        "python", "sql", "pandas", "excel", "postgres", "postgresql", "oracle",
        "linux", "docker", "kubernetes", "spark", "hadoop", "airflow",
        "java", "c#", "javascript", "typescript", "react",
    ]
    skills = sorted({w for w in skill_words if re.search(rf"\b{re.escape(w)}\b", text, re.I)})

    # языки
    lang_dict = {
        "english": r"\b(английский|english|англ)\b",
        "german": r"\b(немецкий|german)\b",
        "french": r"\b(французский|french)\b",
    }
    languages = [k for k, pat in lang_dict.items() if re.search(pat, text, re.I)]

    return {
        "text": text,
        "contacts": {k: v for k, v in {"email": (emails[0] if emails else None), "phone": (phones[0] if phones else None)}.items() if v},
        "skills": skills,
        "languages": languages,
    }

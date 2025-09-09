from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .parser_service import extract_text, parse_resume


_SUPPORTED = {".pdf", ".docx", ".rtf", ".txt"}


def _read_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".rtf":
        # Пытаемся аккуратно распарсить RTF
        try:
            from striprtf.striprtf import rtf_to_text  # type: ignore
            return rtf_to_text(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            # грубая деградация (на случай отсутствия striprtf)
            raw = path.read_text(encoding="utf-8", errors="ignore")
            raw = re.sub(r"\\par[d]?", "\n", raw)
            raw = re.sub(r"{\\.*?}", "", raw)
            raw = re.sub(r"[{}\\]", " ", raw)
            return raw
    # pdf/docx/и пр. — через наш универсальный extract_text
    return extract_text(str(path))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s, flags=re.S).strip().lower()


def _only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


def _resume_dedup_key(doc: Dict) -> str:
    contacts = doc.get("contacts", {}) or {}
    name = _norm(" ".join([contacts.get("last_name", ""),
                           contacts.get("first_name", ""),
                           contacts.get("middle_name", "")]).strip())
    phone = _only_digits(contacts.get("phone", ""))
    email = _norm(contacts.get("email", ""))

    # 1) телефон — самый надёжный
    if phone:
        return f"phone:{phone}"
    # 2) связка имя+email
    if name and email:
        return f"name_email:{name}|{email}"
    # 3) просто email
    if email:
        return f"email:{email}"
    # 4) если всё пусто — хэш нормализованного текста
    text = _norm(doc.get("text", ""))[:2000]  # ограничим, чтобы хэш был стабильным
    return "hash:" + hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _vacancy_dedup_key(text: str) -> str:
    """
    Примерная нормализация: берём заголовок/первые осмысленные строки.
    Если в тексте явно встречается «Вакансия: …» — используем её.
    """
    t = _norm(text)
    m = re.search(r"(?:ваканси[яи]:?\s*)(.+)", t)
    if m:
        hdr = m.group(1)[:120]
    else:
        # первые 1–2 непустые строки
        lines = [ln.strip() for ln in re.split(r"\n+", text) if ln.strip()]
        hdr = " ".join(lines[:2])[:120] if lines else t[:120]
    return "vac:" + hdr


def load_resumes_from_dir(dir_path: str | os.PathLike) -> List[Dict]:
    """
    Сканируем папку с резюме (pdf/docx/rtf/txt), парсим, удаляем дубли.
    Возврат: [{id, text, contacts, skills, languages, source_path}, ...]
    """
    base = Path(dir_path)
    items: List[Dict] = []
    seen: set[str] = set()

    for p in sorted(base.glob("*")):
        if not p.is_file() or p.suffix.lower() not in _SUPPORTED:
            continue

        try:
            text = _read_text_from_file(p)
            doc = parse_resume(text)  # поддерживаем оба формата: путь/текст — parse_resume уже универсальный
        except Exception:
            # надёжно: если не распарсили — хотя бы завернём в текст
            text = _read_text_from_file(p)
            doc = {"text": text, "contacts": {}, "skills": [], "languages": []}

        key = _resume_dedup_key(doc)
        if key in seen:
            continue
        seen.add(key)

        # аккуратное имя кандидата
        contacts = doc.get("contacts", {}) or {}
        display_name = " ".join([
            contacts.get("last_name", ""),
            contacts.get("first_name", ""),
            contacts.get("middle_name", ""),
        ]).strip() or p.stem

        items.append({
            "id": key,               # устойчивый id = ключ дедупликации
            "name": display_name,
            "text": doc.get("text", ""),
            "contacts": contacts,
            "skills": doc.get("skills", []),
            "languages": doc.get("languages", []),
            "source_path": str(p),
        })

    return items


def load_vacancies_from_dir(dir_path: str | os.PathLike) -> List[Dict]:
    """
    Сканируем папку с описаниями вакансий, удаляем дубли.
    Возврат: [{id, title, text, source_path}, ...]
    """
    base = Path(dir_path)
    items: List[Dict] = []
    seen: set[str] = set()

    for p in sorted(base.glob("*")):
        if not p.is_file() or p.suffix.lower() not in _SUPPORTED:
            continue

        try:
            text = _read_text_from_file(p)
        except Exception:
            continue

        key = _vacancy_dedup_key(text)
        if key in seen:
            continue
        seen.add(key)

        # заголовок = первая небустая строка
        lines = [ln.strip() for ln in re.split(r"\n+", text) if ln.strip()]
        title = lines[0][:160] if lines else p.stem

        items.append({
            "id": key,
            "title": title,
            "text": text,
            "source_path": str(p),
        })

    return items

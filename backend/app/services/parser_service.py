"""
Парсер резюме/вакансий из PDF/DOCX/TXT + извлечение контактов.

Зависимости:
- pypdf 4.x  (PDF)
- python-docx (DOCX)  — опционально; если не установлен, DOCX будет пропущен.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, IO
import re
import io
from pypdf import PdfReader

def _read_pdf(stream: IO[bytes], *, max_pages: int | None) -> str:
    reader = PdfReader(stream, strict=False)
    # иногда файлы помечены как зашифрованные, но без пароля — пробуем пустую строку
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")  # type: ignore[attr-defined]
        except Exception:
            pass

    chunks: list[str] = []
    total = len(reader.pages)
    limit = total if max_pages is None else min(total, max_pages)
    for i in range(limit):
        page = reader.pages[i]
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def extract_text(src: str | Path | bytes | IO[bytes], *, max_pages: int | None = None) -> str:
    """
    Достаёт текст из PDF.
    src: путь/байты/поток. max_pages: ограничение по страницам (None = все).
    """
    # 1) путь -> открываем файл
    if isinstance(src, (str, Path)):
        with open(src, "rb") as fh:
            return _read_pdf(fh, max_pages=max_pages)

    # 2) байты -> BytesIO
    if isinstance(src, (bytes, bytearray)):
        return _read_pdf(io.BytesIO(src), max_pages=max_pages)

    # 3) файловый/буферный поток
    if hasattr(src, "read"):
        return _read_pdf(src, max_pages=max_pages)

    raise TypeError("Unsupported src type. Use path | bytes | binary file-like.")


def _read_docx(path: Path) -> str:
    try:
        import docx  # type: ignore
    except Exception as e:
        raise ImportError("Для разбора DOCX установите пакет 'python-docx'") from e
    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs).strip()

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d?[-(\s]?)?(?:\d{3})[-)\s.]?\d{3}[-\s.]?\d{2}[-\s.]?\d{2}")


def parse_contacts(text: str) -> dict:
    """
    Вытаскивает email и телефон (простые регулярки, можно усложнить позже).
    """
    email = None
    phone = None
    em = _EMAIL_RE.search(text)
    if em:
        email = em.group(0)
    ph = _PHONE_RE.search(text)
    if ph:
        phone = ph.group(0)
    return {"email": email, "phone": phone}


DEFAULT_SKILLS = {
    "python", "sql", "postgres", "docker", "kubernetes", "fastapi", "django",
    "pydantic", "pytest", "git", "linux", "rest", "ml", "pandas", "numpy"
}
DEFAULT_LANGS = {
    "english", "английский", "russian", "русский", "german", "немецкий"
}


def _extract_set(words: set[str], text: str) -> list[str]:
    """
    Поиск терминов из множества в тексте (регистр игнорируется).
    Возвращает список найденных (в исходном порядке множества не гарантируем).
    """
    t = text.lower()
    found = [w for w in words if w.lower() in t]
    # Убираем дубликаты и нормализуем порядок
    return sorted(set(found))


def parse_resume(path: str | Path) -> dict[str, Any]:
    """
    Высокоуровневая функция: извлекает текст → контакты → простые признаки.
    Возвращает словарь:
        {
          "text": str,
          "contacts": {"email":..., "phone":...},
          "skills": [..],
          "languages": [..]
        }
    """
    text = extract_text(path)
    contacts = parse_contacts(text)
    skills = _extract_set(DEFAULT_SKILLS, text)
    langs = _extract_set(DEFAULT_LANGS, text)
    return {
        "text": text,
        "contacts": contacts,
        "skills": skills,
        "languages": langs,
    }

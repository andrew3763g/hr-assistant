from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, TypedDict

from backend.app.config import settings
from backend.app.services.gdrive_service import FileMetadata, get_storage
from backend.app.services.parser_service import extract_text, parse_resume
from backend.app.services.ai_matcher_service import rank_candidates

PROJ_ROOT = Path(__file__).resolve().parents[2]
TEMP_DIR = PROJ_ROOT / "temp"
OUT_FILE = TEMP_DIR / "ranked_results.json"

ALIAS = {
    "resumes": ["resumes", "cv", "cvs", "job_applications", "резюме", "Резюме"],
    "vacancies": ["vacancies", "jobs", "job_openings", "вакансии", "Вакансии", "вакансия"],
}

_email_re = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_phone_re = re.compile(r"\+?\d[\d\-\s()]{6,}\d")


class CandidateRecord(TypedDict):
    id: str
    name: str
    text: str


CandidateList = List[CandidateRecord]


def _pick_latest(files: Sequence[FileMetadata]) -> Optional[FileMetadata]:
    def key_fn(metadata: FileMetadata) -> Tuple[bool, datetime]:
        timestamp = metadata.get("modifiedTime") or ""
        try:
            return False, datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            return True, datetime.min

    if not files:
        return None
    return sorted(files, key=key_fn)[-1]


def _signature(text: str) -> Tuple[str, str, str]:
    email_match = _email_re.search(text or "")
    phone_match = _phone_re.search(text or "")
    email = email_match.group(0).lower() if email_match else ""
    phone = phone_match.group(0) if phone_match else ""
    head = (text or "").strip().lower().replace("\n", " ")[:200]
    return email, phone, head


# -------------------- GDRIVE --------------------


def _resolve_folder_key(desired: str, role: str, available: Iterable[str]) -> str:
    desired_variants = [desired, desired.lower(), *ALIAS.get(role, [])]
    for candidate in desired_variants:
        for actual in available:
            if actual == candidate or actual.lower() == candidate.lower():
                return actual
    raise KeyError(
        f"Folder key '{desired}' ({role}) не найден. Доступны: {', '.join(available)}"
    )


def _load_from_gdrive(resumes_key: str, vacancies_key: str) -> Tuple[str, CandidateList]:
    storage = get_storage()
    mapping: dict[str, str] = getattr(settings, "GOOGLE_DRIVE_FOLDERS", {}) or {}

    if not mapping:
        raise AssertionError(
            "GOOGLE_DRIVE_FOLDERS не сконфигурирован. Проверь settings.GOOGLE_DRIVE_FOLDERS_FILE."
        )

    resumes_key = _resolve_folder_key(resumes_key, "resumes", mapping.keys())
    vacancies_key = _resolve_folder_key(vacancies_key, "vacancies", mapping.keys())

    vacancy_meta = _pick_latest(storage.list_files(vacancies_key))
    if not vacancy_meta or "id" not in vacancy_meta:
        raise AssertionError(
            f"В папке '{vacancies_key}' ничего не найдено. Доступные ключи: {list(mapping.keys())}"
        )
    vacancy_text = extract_text(storage.download(vacancy_meta["id"]), max_pages=3)

    cand_files = storage.list_files(resumes_key)
    if not cand_files:
        raise AssertionError(
            f"В папке '{resumes_key}' ничего не найдено. Доступные ключи: {list(mapping.keys())}"
        )

    seen_signatures: set[Tuple[str, str, str]] = set()
    candidates: CandidateList = []
    for index, metadata in enumerate(cand_files, 1):
        file_id = metadata.get("id")
        if not isinstance(file_id, str):
            continue
        try:
            payload = storage.download(file_id)
            text = extract_text(payload, max_pages=2)
            signature = _signature(text)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            resume_doc = parse_resume(payload)
            contacts = resume_doc.get("contacts") if isinstance(resume_doc, dict) else {}
            contact_name = contacts.get("name") if isinstance(contacts, dict) else None
            name = metadata.get("name") or contact_name or f"cand-{index}"
            candidates.append({"id": file_id, "name": name, "text": text})
        except Exception as exc:
            print(f"[skip] {metadata.get('name', file_id)}: {exc}")

    if not candidates:
        raise AssertionError(f"Кандидаты не найдены в папке '{resumes_key}'")

    print(f"[gdrive] keys -> resumes='{resumes_key}', vacancies='{vacancies_key}'")
    return vacancy_text, candidates


# -------------------- LOCAL --------------------


def _iter_files(dirpath: Path) -> Iterable[Path]:
    exts = {".pdf", ".docx", ".rtf"}
    for candidate in dirpath.rglob("*"):
        if candidate.suffix.lower() in exts and candidate.is_file():
            yield candidate


def _load_from_local(resumes_dir: Path, vacancies_dir: Path) -> Tuple[str, CandidateList]:
    vacancy_candidates = list(_iter_files(vacancies_dir))
    if not vacancy_candidates:
        raise AssertionError(f"В папке '{vacancies_dir}' ничего не найдено.")
    vacancy_path = sorted(vacancy_candidates, key=lambda item: item.stat().st_mtime)[-1]
    vacancy_text = extract_text(vacancy_path.read_bytes(), max_pages=3)

    resume_files = list(_iter_files(resumes_dir))
    if not resume_files:
        raise AssertionError(f"В папке '{resumes_dir}' ничего не найдено.")

    seen_signatures: set[Tuple[str, str, str]] = set()
    candidates: CandidateList = []
    for index, path in enumerate(resume_files, 1):
        try:
            payload = path.read_bytes()
            text = extract_text(payload, max_pages=2)
            signature = _signature(text)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            resume_doc = parse_resume(payload)
            contacts = resume_doc.get("contacts") if isinstance(resume_doc, dict) else {}
            contact_name = contacts.get("name") if isinstance(contacts, dict) else None
            name = contact_name or path.stem
            candidates.append({"id": path.name, "name": name, "text": text})
        except Exception as exc:
            print(f"[skip] {path.name}: {exc}")

    if not candidates:
        raise AssertionError(f"Кандидаты не найдены в '{resumes_dir}'")

    print(f"[local] resumes='{resumes_dir}', vacancies='{vacancies_dir}'")
    return vacancy_text, candidates


# -------------------- MAIN --------------------


def main(
    backend: str,
    top_k: int,
    model: str,
    resumes_key: str,
    vacancies_key: str,
    resumes_dir: Path,
    vacancies_dir: Path,
) -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    if backend == "auto":
        backend = settings.STORAGE_BACKEND

    if backend.lower() == "gdrive":
        vacancy_text, candidates = _load_from_gdrive(resumes_key, vacancies_key)
    else:
        vacancy_text, candidates = _load_from_local(resumes_dir, vacancies_dir)

    ranking = rank_candidates(
        vacancy_text,
        candidates,
        top_k=top_k,
        model=model,
        passphrase=getattr(settings, "OPENAI_KEY_PASSPHRASE", None),
    )

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "backend": backend,
        "top_k": top_k,
        "results": ranking,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT_FILE}")
    for index, result in enumerate(ranking[:min(top_k, 10)], 1):
        print(f"{index:>2}. {result['name']} — {result['score']}  ({result['id']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rank candidates from storage.")
    parser.add_argument("--backend", choices=["auto", "gdrive", "local"], default="auto")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--resumes-key", type=str, default="resumes")
    parser.add_argument("--vacancies-key", type=str, default="vacancies")
    parser.add_argument("--resumes-dir", type=Path, default=PROJ_ROOT / "inbox" / "job_applications")
    parser.add_argument("--vacancies-dir", type=Path, default=PROJ_ROOT / "inbox" / "job_openings")

    args = parser.parse_args()
    main(
        backend=args.backend,
        top_k=args.top_k,
        model=args.model,
        resumes_key=args.resumes_key,
        vacancies_key=args.vacancies_key,
        resumes_dir=args.resumes_dir,
        vacancies_dir=args.vacancies_dir,
    )


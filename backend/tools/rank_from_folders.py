# backend/tools/rank_from_folders.py
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Iterable

from backend.app.config import settings
from backend.app.services.gdrive_service import get_storage
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


def _pick_latest(files: List[Dict]) -> Dict:
    def key_fn(f: Dict) -> Tuple[bool, datetime]:
        ts = f.get("modifiedTime") or ""
        try:
            return (False, datetime.fromisoformat(ts.replace("Z", "+00:00")))
        except Exception:
            return (True, datetime.min)
    return sorted(files, key=key_fn)[-1] if files else {}


def _signature(text: str) -> Tuple[str, str, str]:
    email = (_email_re.search(text or "") or [""])[0].lower()
    phone = (_phone_re.search(text or "") or [""])[0]
    head = (text or "").strip().lower().replace("\n", " ")[:200]
    return (email, phone, head)


# -------------------- GDRIVE --------------------

def _resolve_folder_key(desired: str, role: str, available: Iterable[str]) -> str:
    """
    Вернёт первый подходящий ключ для роли (resumes/vacancies) среди доступных.
    Учитывает алиасы и регистр.
    """
    desired_list = [desired, desired.lower()]
    desired_list += ALIAS.get(role, [])
    for k in desired_list:
        for avail in available:
            if avail == k or avail.lower() == k.lower():
                return avail
    raise KeyError(
        f"Folder key '{desired}' ({role}) не найден. Доступны: {', '.join(available)}"
    )


def _load_from_gdrive(resumes_key: str, vacancies_key: str) -> Tuple[str, List[Dict]]:
    storage = get_storage()  # учитывает settings.STORAGE_BACKEND
    mapping: Dict[str, str] = getattr(settings, "GOOGLE_DRIVE_FOLDERS", {}) or {}

    if not mapping:
        # подскажем пользователю, что в конфиге пусто
        raise AssertionError(
            "GOOGLE_DRIVE_FOLDERS не сконфигурирован. Проверь settings.GOOGLE_DRIVE_FOLDERS_FILE."
        )

    # подобрать реальные ключи с учётом алиасов
    resumes_key = _resolve_folder_key(resumes_key, "resumes", mapping.keys())
    vacancies_key = _resolve_folder_key(vacancies_key, "vacancies", mapping.keys())

    vac_files = storage.list_files(vacancies_key)
    if not vac_files:
        raise AssertionError(f"В папке '{vacancies_key}' ничего не найдено. Доступные ключи: {list(mapping.keys())}")
    vacancy_meta = _pick_latest(vac_files)
    vacancy_bytes = storage.download(vacancy_meta["id"])
    vacancy_text = extract_text(vacancy_bytes, max_pages=3)

    cand_files = storage.list_files(resumes_key)
    if not cand_files:
        raise AssertionError(f"В папке '{resumes_key}' ничего не найдено. Доступные ключи: {list(mapping.keys())}")

    seen = set()
    candidates: List[Dict] = []
    for i, f in enumerate(cand_files, 1):
        try:
            data = storage.download(f["id"])
            txt = extract_text(data, max_pages=2)
            sig = _signature(txt)
            if sig in seen:
                continue
            seen.add(sig)
            doc = parse_resume(data)
            name = f.get("name") or (doc.get("contacts", {}) or {}).get("name") or f"cand-{i}"
            candidates.append({"id": f["id"], "name": name, "text": txt})
        except Exception as e:
            print(f"[skip] {f.get('name')}: {e}")

    if not candidates:
        raise AssertionError(f"Кандидаты не найдены в папке '{resumes_key}'")

    print(f"[gdrive] keys -> resumes='{resumes_key}', vacancies='{vacancies_key}'")
    return vacancy_text, candidates


# -------------------- LOCAL --------------------

def _iter_files(dirpath: Path) -> Iterable[Path]:
    exts = {".pdf", ".docx", ".rtf"}
    for p in dirpath.rglob("*"):
        if p.suffix.lower() in exts and p.is_file():
            yield p


def _load_from_local(resumes_dir: Path, vacancies_dir: Path) -> Tuple[str, List[Dict]]:
    vac_files = list(_iter_files(vacancies_dir))
    if not vac_files:
        raise AssertionError(f"В папке '{vacancies_dir}' ничего не найдено.")
    vac = sorted(vac_files, key=lambda p: p.stat().st_mtime)[-1]
    vacancy_text = extract_text(vac.read_bytes(), max_pages=3)

    cand_files = list(_iter_files(resumes_dir))
    if not cand_files:
        raise AssertionError(f"В папке '{resumes_dir}' ничего не найдено.")

    seen = set()
    candidates: List[Dict] = []
    for i, p in enumerate(cand_files, 1):
        try:
            data = p.read_bytes()
            txt = extract_text(data, max_pages=2)
            sig = _signature(txt)
            if sig in seen:
                continue
            seen.add(sig)
            doc = parse_resume(data)
            name = (doc.get("contacts", {}) or {}).get("name") or p.stem
            candidates.append({"id": p.name, "name": name, "text": txt})
        except Exception as e:
            print(f"[skip] {p.name}: {e}")

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
    for i, r in enumerate(ranking[:min(top_k, 10)], 1):
        print(f"{i:>2}. {r['name']} — {r['score']}  ({r['id']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rank candidates from storage.")
    parser.add_argument("--backend", choices=["auto", "gdrive", "local"], default="auto")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--model", type=str, default="gpt-4o-mini")

    # gdrive keys (допускаются рус/англ)
    parser.add_argument("--resumes-key", type=str, default="resumes")
    parser.add_argument("--vacancies-key", type=str, default="vacancies")

    # local dirs (по умолчанию твои структуры из /inbox)
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

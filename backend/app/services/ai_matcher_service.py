# backend/app/services/ai_matcher_service.py
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI, OpenAIError

# Конфиг может отсутствовать в изолированных тестах
try:
    from backend.app.config import settings  # type: ignore
except Exception:  # pragma: no cover
    settings = None  # noqa: N816

from backend.app.services.api_key_manager import APIKeyManager

__all__ = ["rank_candidates"]


# -------------------- helpers --------------------

def _get_passphrase(explicit: Optional[str] = None) -> Optional[str]:
    """
    Источник пароля для расшифровки:
      1) аргумент функции,
      2) settings.OPENAI_KEY_PASSPHRASE,
      3) переменная окружения OPENAI_KEY_PASSPHRASE.
    """
    if explicit:
        return explicit
    if settings is not None and hasattr(settings, "OPENAI_KEY_PASSPHRASE"):
        try:
            val = getattr(settings, "OPENAI_KEY_PASSPHRASE")
            if val:
                return str(val)
        except Exception:
            pass
    return os.getenv("OPENAI_KEY_PASSPHRASE")


def _ensure_openai_client(passphrase: Optional[str] = None) -> OpenAI:
    """
    Порядок поиска ключа:
      - OPENAI_API_KEY в окружении,
      - шифро-хранилище (api_keys.enc) через APIKeyManager и passphrase,
      - best-effort без пароля (если файл сохранён незашифрованно).
    """
    if os.getenv("OPENAI_API_KEY"):
        return OpenAI()

    pp = _get_passphrase(passphrase)
    if pp:
        km = APIKeyManager()
        key = km.get("openai", passphrase=pp)
        if key:
            return OpenAI(api_key=key)

    try:
        km = APIKeyManager()
        key = km.get("openai")
        if key:
            return OpenAI(api_key=key)
    except Exception:
        pass

    raise OpenAIError(
        "OpenAI API key not found. Set OPENAI_API_KEY env var or provide "
        "passphrase to unlock encrypted store via APIKeyManager."
    )


def _only_json(text: str) -> str:
    """Возвращает первый JSON-массив из ответа модели (вырезая обрамляющий текст)."""
    m = re.search(r"\[\s*{.*?}\s*\]", text, flags=re.S)
    if m:
        return m.group(0).strip()
    m = re.search(r'"items"\s*:\s*(\[\s*{.*?}\s*\])', text, flags=re.S)
    if m:
        return m.group(1).strip()
    return text.strip()


# -------------------- public API --------------------

def rank_candidates(
    vacancy_text: str,
    candidates: List[Dict[str, Any]],
    *,
    top_k: int = 5,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    weights: Optional[Dict[str, float]] = None,
    passphrase: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    AI-ранжирование кандидатов под вакансию.

    candidates: [{"id": "...", "name": "...", "text": "..."}]
    Возврат: [{"index": int, "id": str, "name": str, "score": int, "reasons": str}, ...]
    """
    if not candidates:
        return []

    weights = weights or {"skills": 4, "recent": 3, "communication": 2, "culture": 1}

    client = _ensure_openai_client(passphrase)

    # Подготовим компактный ввод
    blocks = []
    for i, c in enumerate(candidates):
        cid = c.get("id", f"cand-{i+1}")
        name = c.get("name", cid)
        text = (c.get("text") or "").strip()
        blocks.append(f"### [{i}] {name} ({cid})\n{text}")
    cand_blob = "\n\n".join(blocks)

    system_msg = (
        "You are an experienced technical recruiter. Rank candidates for a vacancy. "
        "Consider skill relevance, recency of experience, communication clarity, and culture fit. "
        "Score each candidate from 0 to 100.\n"
        "Bias controls: do NOT over-reward extremely long careers; penalize outdated stacks; "
        "allow promising near-misses if other signals are strong.\n"
        "Output strictly a JSON array of objects with fields: "
        '{"index": <int>, "score": <int>, "reasons": "<short justification>"} '
        "(index is the order provided). No extra text."
    )

    user_msg = (
        f"VACANCY:\n{vacancy_text.strip()}\n\n"
        f"WEIGHTS: {json.dumps(weights)}\n\n"
        f"CANDIDATES:\n{cand_blob}\n\n"
        "Return top candidates with balanced judgment according to the weights."
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    )

    content = (resp.choices[0].message.content or "").strip()
    payload = _only_json(content)

    # Попытка распарсить ответ модели
    items: List[Dict[str, Any]]
    try:
        parsed = json.loads(payload)
        if isinstance(parsed, dict) and "items" in parsed:
            parsed = parsed["items"]
        if not isinstance(parsed, list):
            raise ValueError("model output is not a list")
        items = parsed
    except Exception:
        # ---------- Переписанная fallback-эвристика ----------
        # 1) Пересечение ключевых слов вакансии и резюме
        vocab = set(
            w.lower()
            for w in re.findall(r"[A-Za-zА-Яа-я0-9_+.#-]{2,}", vacancy_text, flags=re.U)
        )

        def _overlap_score(txt: str) -> int:
            if not vocab:
                return 0
            words = set(
                w.lower()
                for w in re.findall(r"[A-Za-zА-Яа-я0-9_+.#-]{2,}", txt or "", flags=re.U)
            )
            inter = len(vocab & words)
            return min(100, int(100 * inter / (len(vocab) + 1)))

        # 2) Длина текста как прокси «насыщенности» (очень грубо)
        def _length_score(txt: str) -> int:
            words = len(re.findall(r"\w{2,}", txt or "", flags=re.U))
            return max(0, min(100, 15 + words // 15))

        items = []
        for i, c in enumerate(candidates):
            txt = c.get("text") or ""
            score = int(round(0.6 * _overlap_score(txt) + 0.4 * _length_score(txt)))
            items.append(
                {
                    "index": i,
                    "score": score,
                    "reasons": "Fallback: keyword overlap + length heuristic.",
                }
            )

    # Нормализация и добавление id/name
    normalized: List[Dict[str, Any]] = []
    for it in items:
        try:
            idx = int(it.get("index"))
        except Exception:
            continue
        if not (0 <= idx < len(candidates)):
            continue

        score = int(it.get("score", 0))
        reasons = str(it.get("reasons", "")).strip()
        c = candidates[idx]
        normalized.append(
            {
                "index": idx,
                "id": c.get("id", f"cand-{idx+1}"),
                "name": c.get("name", f"cand-{idx+1}"),
                "score": max(0, min(100, score)),
                "reasons": reasons,
            }
        )

    normalized.sort(key=lambda x: x["score"], reverse=True)
    if top_k and top_k > 0:
        normalized = normalized[:top_k]
    return normalized

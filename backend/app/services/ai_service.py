# backend/app/services/ai_service.py
from __future__ import annotations
import json
from typing import Tuple, Dict, Any, List, Optional

from openai import OpenAI
from backend.app.config import settings

_client = OpenAI()  # ключ берём из окружения/менеджера ключей

SYSTEM_PROMPT = (
    "You are a hiring assistant. Score candidate fitness for a vacancy strictly 0-100.\n"
    "Return STRICT JSON: {\"score\": <int>, \"reasons\": [<string>...] }.\n"
    "Be concise. No prose outside JSON."
)

def score_match(
    vacancy_text: str,
    candidate_text: str,
    weights: Optional[Dict[str, int]] = None,
    model: Optional[str] = None,
) -> Tuple[int, str]:
    """
    Возвращает (score, reasoning). reasoning — склейка reasons, удобна для gpt_match_reasoning.
    """
    model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    user = (
        f"VACANCY:\n{vacancy_text}\n\n"
        f"CANDIDATE:\n{candidate_text}\n\n"
        f"WEIGHTS (optional): {json.dumps(weights or {}, ensure_ascii=False)}"
    )

    resp = _client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=400,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    )

    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"score": 0, "reasons": ["Model returned non-JSON response"]}

    score = int(data.get("score", 0))
    reasons = data.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    reasoning = "\n".join(str(r).strip() for r in reasons if r)

    return score, reasoning

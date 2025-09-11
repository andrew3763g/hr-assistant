from __future__ import annotations
from typing import Dict, Any, Iterable
import re

def _tokenize(s: str) -> set[str]:
    return set(re.findall(r"[a-zA-Zа-яА-Я0-9_#+]{2,}", (s or "").lower()))

def match_resume_to_vacancy(parsed: Dict[str, Any], vacancy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Простой baseline: jaccard по токенам резюме vs. требований вакансии.
    Также учитываем списки skills/languages, если есть.
    """
    resume_text = " ".join([parsed.get("text","")] + parsed.get("skills",[]) + parsed.get("languages",[]))
    vacancy_text = " ".join([vacancy.get("description","")] + vacancy.get("skills",[]) + vacancy.get("languages",[]))

    a, b = _tokenize(resume_text), _tokenize(vacancy_text)
    inter = len(a & b)
    union = max(1, len(a | b))
    jaccard = inter / union

    return {
        "jaccard": jaccard,
        "common_tokens": sorted(list((a & b)))[:100],
        "resume_tokens": len(a),
        "vacancy_tokens": len(b),
    }

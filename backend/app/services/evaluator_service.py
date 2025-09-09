from __future__ import annotations
from typing import Dict, Any, Iterable
import math, re

def evaluate_resume(parsed: Dict[str, Any], criteria: Dict[str, Any]) -> Dict[str, Any]:
    """
    Базовая эвристика: +1 за каждое совпадение скилла, вес за «обязательные»,
    доп.баллы за языки и опыт.
    """
    score = 0.0
    max_score = 0.0
    details: list[dict] = []

    skills_need: Iterable[str] = map(str.lower, criteria.get("skills", []))
    resume_skills: set[str] = set(map(str.lower, parsed.get("skills", [])))

    # skills
    for s in skills_need:
        max_score += 1
        hit = s in resume_skills
        if hit:
            score += 1
        details.append({"metric": f"skill:{s}", "hit": hit, "weight": 1})

    # languages
    req_langs = set(map(str.lower, criteria.get("languages", [])))
    res_langs = set(map(str.lower, parsed.get("languages", [])))
    if req_langs:
        max_score += 1
        hit = bool(req_langs & res_langs)
        if hit: score += 1
        details.append({"metric": "languages", "hit": hit, "weight": 1})

    # опыт лет — грубо по регулярке в исходном тексте
    text = (parsed.get("text") or "").lower()
    years_req = int(criteria.get("min_years", 0))
    if years_req:
        max_score += 1
        found = 0
        for m in re.finditer(r"(\d+)\s*(?:год|лет|года)", text):
            try:
                found = max(found, int(m.group(1)))
            except Exception: pass
        hit = found >= years_req
        if hit: score += 1
        details.append({"metric": "years", "hit": hit, "weight": 1, "found": found, "need": years_req})

    return {
        "score": score,
        "max_score": max_score,
        "ratio": (score / max_score) if max_score else 0,
        "details": details,
    }

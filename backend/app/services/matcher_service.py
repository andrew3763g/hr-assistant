from __future__ import annotations
"""
Бэйзлайн-сопоставление кандидата и вакансии.
Считает Jaccard-сходство по навыкам и языкам и агрегирует в общий балл.
"""
from typing import Iterable


def _to_set(items: Iterable[str] | None) -> set[str]:
    return {i.strip().lower() for i in (items or []) if i and i.strip()}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def match_candidate_to_vacancy(cand: dict, vac: dict) -> dict:
    """
    cand: {"skills": [...], "languages": [...]}
    vac:  {"skills": [...], "languages": [...]}
    Возвращает:
      {"score": float, "details": {"skills": float, "languages": float}}
    """
    cs = _to_set(cand.get("skills"))
    vs = _to_set(vac.get("skills"))
    cl = _to_set(cand.get("languages"))
    vl = _to_set(vac.get("languages"))

    s_skills = _jaccard(cs, vs)
    s_langs = _jaccard(cl, vl)

    # Простое усреднение (можно задать веса позже)
    score = (s_skills + s_langs) / 2.0
    return {
        "score": round(score, 4),
        "details": {
            "skills": round(s_skills, 4),
            "languages": round(s_langs, 4),
            "intersect_skills": sorted(cs & vs),
            "missing_skills": sorted(vs - cs),
        },
    }

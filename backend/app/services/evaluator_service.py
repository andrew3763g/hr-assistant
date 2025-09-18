from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Set, TypedDict, cast


class EvaluationDetail(TypedDict, total=False):
    metric: str
    hit: bool
    weight: float
    found: int
    need: int


class EvaluationResult(TypedDict):
    score: float
    max_score: float
    ratio: float
    details: List[EvaluationDetail]


def _not_string_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _to_lower_iter(items: Iterable[object]) -> Iterable[str]:
    for item in items:
        yield str(item).lower()


def evaluate_resume(parsed: dict[str, object], criteria: dict[str, object]) -> EvaluationResult:
    """Heuristic scoring of resume vs. criteria using simple keyword matches."""
    score = 0.0
    max_score = 0.0
    details: List[EvaluationDetail] = []

    raw_required_skills = criteria.get("skills", [])
    skills_need: Iterable[str]
    if _not_string_sequence(raw_required_skills):
        skills_need = _to_lower_iter(cast(Sequence[object], raw_required_skills))
    else:
        skills_need = ()

    raw_resume_skills = parsed.get("skills", [])
    if _not_string_sequence(raw_resume_skills):
        resume_skills: Set[str] = set(_to_lower_iter(cast(Sequence[object], raw_resume_skills)))
    else:
        resume_skills = set[str]()

    for skill in skills_need:
        max_score += 1
        hit = skill in resume_skills
        if hit:
            score += 1
        details.append({"metric": f"skill:{skill}", "hit": hit, "weight": 1.0})

    raw_req_languages = criteria.get("languages", [])
    if _not_string_sequence(raw_req_languages):
        req_langs: Set[str] = set(_to_lower_iter(cast(Sequence[object], raw_req_languages)))
    else:
        req_langs = set[str]()

    raw_res_languages = parsed.get("languages", [])
    if _not_string_sequence(raw_res_languages):
        res_langs: Set[str] = set(_to_lower_iter(cast(Sequence[object], raw_res_languages)))
    else:
        res_langs = set[str]()

    if req_langs:
        max_score += 1
        hit = bool(req_langs & res_langs)
        if hit:
            score += 1
        details.append({"metric": "languages", "hit": hit, "weight": 1.0})

    raw_text = parsed.get("text")
    text = str(raw_text).lower() if raw_text is not None else ""
    raw_min_years = criteria.get("min_years", 0)
    if isinstance(raw_min_years, (int, float)):
        years_req = int(raw_min_years)
    elif isinstance(raw_min_years, str) and raw_min_years.isdigit():
        years_req = int(raw_min_years)
    else:
        years_req = 0

    if years_req:
        max_score += 1
        found = 0
        for match in re.finditer(r"(\d+)\s*(?:год|лет|года)", text):
            value = match.group(1)
            try:
                found = max(found, int(value))
            except ValueError:
                continue
        hit = found >= years_req
        if hit:
            score += 1
        details.append(
            {
                "metric": "years",
                "hit": hit,
                "weight": 1.0,
                "found": found,
                "need": years_req,
            }
        )

    ratio = (score / max_score) if max_score else 0.0
    return {
        "score": score,
        "max_score": max_score,
        "ratio": ratio,
        "details": details,
    }

from __future__ import annotations

from typing import List, Optional, TypedDict, cast

from sqlalchemy.orm import Session

from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.models.vacancy_match import VacancyMatch
from backend.app.services.ai_service import MatchScore, score_match

DEFAULT_WEIGHTS: dict[str, int] = {"skills": 4, "recent": 3, "communication": 2, "culture": 1}


class RankedCandidate(TypedDict):
    candidate_id: int
    score: int
    details: MatchScore


def _text_value(*values: Optional[str]) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _ensure_match(entry: Optional[VacancyMatch], *, vacancy_id: int, candidate_id: int) -> VacancyMatch:
    if entry is not None:
        return entry
    return VacancyMatch(vacancy_id=vacancy_id, candidate_id=candidate_id)


def rank_candidates_for_vacancy(
    db: Session,
    vacancy_id: int,
    top_k: int = 5,
    weights: Optional[dict[str, int]] = None,
) -> List[RankedCandidate]:
    weights = weights or DEFAULT_WEIGHTS

    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if vacancy is None:
        return []

    raw_vacancy_id = getattr(vacancy, "id", None)
    if not isinstance(raw_vacancy_id, int):
        return []
    vacancy_id_value = raw_vacancy_id

    vacancy_text = _text_value(
        cast(Optional[str], getattr(vacancy, "original_text", None)),
        cast(Optional[str], getattr(vacancy, "description", None)),
    )
    if not vacancy_text:
        return []

    candidates = db.query(Candidate).all()
    ranked: List[RankedCandidate] = []

    for candidate in candidates:
        raw_candidate_id = getattr(candidate, "id", None)
        if not isinstance(raw_candidate_id, int):
            continue
        candidate_id_value = raw_candidate_id

        candidate_text = _text_value(cast(Optional[str], getattr(candidate, "original_text", None)))
        if not candidate_text:
            continue

        score_data = score_match(vacancy_text, candidate_text)
        score = int(score_data["score"])

        existing_match = (
            db.query(VacancyMatch)
            .filter(
                VacancyMatch.vacancy_id == vacancy_id_value,
                VacancyMatch.candidate_id == candidate_id_value,
            )
            .first()
        )
        match_entry = _ensure_match(existing_match, vacancy_id=vacancy_id_value, candidate_id=candidate_id_value)
        setattr(match_entry, "score", score)
        if existing_match is None:
            db.add(match_entry)

        ranked.append(
            {
                "candidate_id": candidate_id_value,
                "score": score,
                "details": score_data,
            }
        )

    db.commit()
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]

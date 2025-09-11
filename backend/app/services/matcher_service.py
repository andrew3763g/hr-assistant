# backend/app/services/matcher_service.py
from __future__ import annotations
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from backend.app.models.vacancy import Vacancy
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy_match import VacancyMatch
from backend.app.services.ai_service import score_match


def _best_text_for_vacancy(v: Vacancy) -> str:
    # бери самое информативное: summary -> description -> original_text
    return (getattr(v, "gpt_summary", None)
            or getattr(v, "description", None)
            or getattr(v, "original_text", None)
            or "").strip()


def _best_text_for_candidate(c: Candidate) -> str:
    # аналогично: summary -> resume_text -> gpt_strengths -> ...
    return (getattr(c, "gpt_summary", None)
            or getattr(c, "resume_text", None)
            or getattr(c, "gpt_strengths", None)
            or "").strip()


def rank_candidates(
    db: Session,
    vacancy_id: int,
    top_k: int = 5,
    weights: Optional[Dict[str, int]] = None,
    candidate_limit: int = 50,
) -> List[Dict[str, Any]]:
    v = db.get(Vacancy, vacancy_id)
    if not v:
        raise ValueError(f"Vacancy {vacancy_id} not found")

    v_text = _best_text_for_vacancy(v)

    # Выбираем пачку кандидатов (упростим: все/первые N)
    cands = db.query(Candidate).limit(candidate_limit).all()

    results: List[Dict[str, Any]] = []
    for c in cands:
        c_text = _best_text_for_candidate(c)
        if not v_text or not c_text:
            continue

        score, reasoning = score_match(v_text, c_text, weights=weights)

        # UPSERT в vacancy_matches
        vm = (
            db.query(VacancyMatch)
              .filter_by(vacancy_id=vacancy_id, candidate_id=c.id)
              .one_or_none()
        )
        if vm is None:
            vm = VacancyMatch(vacancy_id=vacancy_id, candidate_id=c.id)

        vm.score = score
        # колонка есть у тебя — если у кого-то её нет, строку можно закомментить
        if hasattr(VacancyMatch, "gpt_match_reasoning"):
            vm.gpt_match_reasoning = reasoning

        db.add(vm)
        db.flush()

        results.append({
            "candidate_id": c.id,
            "candidate_name": f"{getattr(c,'first_name','')} {getattr(c,'last_name','')}".strip(),
            "score": score,
            "reasoning": reasoning,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    db.commit()
    return results[:top_k]

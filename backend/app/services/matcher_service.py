# backend/app/services/matcher_service.py
from __future__ import annotations
from typing import Dict, List
from sqlalchemy.orm import Session

from backend.app.models.vacancy import Vacancy
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy_match import VacancyMatch
from backend.app.services.ai_service import score_match

DEFAULT_WEIGHTS = {"skills": 4, "recent": 3, "communication": 2, "culture": 1}

def rank_candidates_for_vacancy(
    db: Session,
    vacancy_id: int,
    top_k: int = 5,
    weights: Dict[str, int] | None = None,
) -> List[Dict]:
    weights = weights or DEFAULT_WEIGHTS

    vac: Vacancy | None = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vac:
        return []

    vtext = vac.original_text or (vac.description or "")
    if not vtext.strip():
        return []

    candidates = db.query(Candidate).all()
    results = []
    for c in candidates:
        rtext = c.original_text or ""
        if not rtext.strip():
            continue
        sj = score_match(vtext, rtext)  # {score, skills_coverage, ...}
        score = int(sj.get("score", 0))

        # апсертим в vacancy_matches (если нужна история — можно не перезаписывать)
        vm = (
            db.query(VacancyMatch)
              .filter(VacancyMatch.vacancy_id == vac.id,
                      VacancyMatch.candidate_id == c.id)
              .first()
        )
        if not vm:
            vm = VacancyMatch(vacancy_id=vac.id, candidate_id=c.id, score=score)
            db.add(vm)
        else:
            vm.score = score

        results.append({
            "candidate_id": c.id,
            "score": score,
            "details": sj,
        })

    db.commit()
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

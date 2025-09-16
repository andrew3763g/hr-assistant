# backend/app/api/matching.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.services.matcher_service import rank_candidates_for_vacancy

router = APIRouter(prefix="/matching", tags=["Matching"])

def get_db():
    with SessionLocal() as db:
        yield db

class RankRequest(BaseModel):
    vacancy_id: int
    top_k: int = 5
    weights: dict[str, int] | None = None

@router.post("/rank")
def rank(req: RankRequest, db: Session = Depends(get_db)):
    items = rank_candidates_for_vacancy(
        db, vacancy_id=req.vacancy_id, top_k=req.top_k, weights=req.weights
    )
    return {"items": items}

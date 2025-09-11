# backend/app/api/matching.py
from __future__ import annotations
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.database import SessionLocal
from backend.app.services.matcher_service import rank_candidates

router = APIRouter(prefix="/matching", tags=["matching"])

class RankRequest(BaseModel):
    vacancy_id: int
    top_k: int = 5
    weights: Optional[Dict[str, int]] = None  # {"skills":4, "recent":3, ...}

@router.post("/rank")
def rank(req: RankRequest):
    try:
        with SessionLocal() as db:
            items = rank_candidates(
                db=db,
                vacancy_id=req.vacancy_id,
                top_k=req.top_k,
                weights=req.weights or {},
            )
            return {"items": items, "count": len(items)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

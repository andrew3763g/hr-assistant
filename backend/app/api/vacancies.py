# backend/app/api/vacancies.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.database import SessionLocal
from backend.app.models.vacancy import Vacancy

router = APIRouter(prefix="/vacancies", tags=["vacancies"])

class VacancyCreate(BaseModel):
    title: str
    description: str

@router.post("")
def create_vacancy(payload: VacancyCreate):
    with SessionLocal() as db:
        v = Vacancy(title=payload.title, description=payload.description)
        db.add(v); db.commit(); db.refresh(v)
        return {"id": v.id}

@router.get("/{vacancy_id}")
def get_vacancy(vacancy_id: int):
    with SessionLocal() as db:
        v = db.get(Vacancy, vacancy_id)
        if not v:
            raise HTTPException(404, "Vacancy not found")
        return {"id": v.id, "title": v.title, "description": v.description}

# backend/app/api/imports.py
from fastapi import APIRouter
from backend.app.database import SessionLocal
from backend.app.services.ingest_service import ingest_all

router = APIRouter(prefix="/import", tags=["import"])

@router.post("/resumes")
def import_resumes():
    with SessionLocal() as db:
        count = ingest_all(db, kind="resumes")
        return {"imported": count}

@router.post("/vacancies")
def import_vacancies():
    with SessionLocal() as db:
        count = ingest_all(db, kind="vacancies")
        return {"imported": count}

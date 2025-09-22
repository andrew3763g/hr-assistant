# backend/app/api/imports.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.ingest_service import ingest_all

router = APIRouter(tags=["Imports"])        # <--- без prefix!


@router.post("/resumes")
async def import_resumes(db: Session = Depends(get_db)):
    count = ingest_all(db, kind="resumes")
    return {"imported": count}


@router.post("/vacancies")
async def import_vacancies(db: Session = Depends(get_db)):
    count = ingest_all(db, kind="vacancies")
    return {"imported": count}

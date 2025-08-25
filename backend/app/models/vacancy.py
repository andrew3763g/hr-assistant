# backend/app/schemas/vacancy.py
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class VacancyBase(BaseModel):
    title: str
    department: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = []
    skills: Optional[List[str]] = []
    questions_template: Optional[List[str]] = []
    evaluation_criteria: Optional[Dict] = {}


class VacancyCreate(VacancyBase):
    pass


class VacancyResponse(VacancyBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# -------------------
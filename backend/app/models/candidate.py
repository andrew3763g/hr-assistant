# backend/app/schemas/candidate.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


class CandidateBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateResponse(CandidateBase):
    id: int
    parsed_skills: Optional[List[str]] = []
    experience_years: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

# -------------------
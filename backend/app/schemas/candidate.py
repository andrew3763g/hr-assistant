# backend/app/schemas/candidate.py
"""Pydantic v2 схемы для работы с кандидатами"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class CandidateStatus(str, Enum):
    NEW = "new"
    PARSED = "parsed"
    MATCHED = "matched"
    INVITED = "invited"
    INTERVIEW_SCHEDULED = "scheduled"
    INTERVIEW_COMPLETED = "completed"
    EVALUATING = "evaluating"
    APPROVED = "approved"
    RESERVED = "reserved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NOT_SPECIFIED = "not_specified"


class EducationLevel(str, Enum):
    SECONDARY = "secondary"
    SECONDARY_SPECIAL = "secondary_special"
    INCOMPLETE_HIGHER = "incomplete_higher"
    BACHELOR = "bachelor"
    MASTER = "master"
    SPECIALIST = "specialist"
    PHD = "phd"
    DOCTOR = "doctor"


class CandidateBase(BaseModel):
    """Базовая схема кандидата"""
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    
    gender: Optional[Gender] = Gender.NOT_SPECIFIED
    birth_date: Optional[datetime] = None
    age: Optional[int] = Field(None, ge=14, le=100)
    
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    
    citizenship: str = Field(default="РФ", max_length=100)
    has_second_citizenship: bool = False
    languages: Dict[str, str] = Field(default_factory=dict)


class CandidateCreate(CandidateBase):
    """Схема для создания кандидата"""
    resume_text: Optional[str] = None
    resume_file_path: Optional[str] = None
    resume_gdrive_id: Optional[str] = None


class CandidateUpdate(BaseModel):
    """Схема для обновления кандидата"""
    model_config = ConfigDict(from_attributes=True)
    
    position_desired: Optional[str] = None
    salary_expectation: Optional[int] = None
    
    total_experience_years: Optional[float] = None
    relevant_experience_years: Optional[float] = None
    last_position: Optional[str] = None
    last_company: Optional[str] = None
    
    education_level: Optional[EducationLevel] = None
    education_institution: Optional[str] = None
    education_speciality: Optional[str] = None
    has_degree: Optional[bool] = None
    
    core_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    
    status: Optional[CandidateStatus] = None


class CandidateResponse(CandidateBase):
    """Схема для ответа с данными кандидата"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    
    position_desired: Optional[str] = None
    salary_expectation: Optional[int] = None
    
    total_experience_years: Optional[float] = None
    relevant_experience_years: Optional[float] = None
    last_position: Optional[str] = None
    last_company: Optional[str] = None
    
    education_level: Optional[EducationLevel] = None
    education_institution: Optional[str] = None
    education_speciality: Optional[str] = None
    has_degree: bool = False
    
    core_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    
    status: CandidateStatus
    is_active: bool = True
    is_verified: bool = False
    has_red_flags: bool = False
    
    created_at: datetime
    updated_at: datetime


class CandidateWithStats(CandidateResponse):
    """Схема кандидата со статистикой"""
    interviews_count: int = 0
    evaluations_count: int = 0
    matches_count: int = 0
    average_score: Optional[float] = None


class CandidateFilter(BaseModel):
    """Схема для фильтрации кандидатов"""
    status: Optional[CandidateStatus] = None
    gender: Optional[Gender] = None
    location: Optional[str] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    education_level: Optional[EducationLevel] = None
    has_red_flags: Optional[bool] = None
    is_active: Optional[bool] = True
    
    skills: Optional[List[str]] = None

    @field_validator('skills')
    def _validate_skills(cls, v: Optional[List[str]]):
        if v and len(v) > 20:
            raise ValueError("Max 20 skills allowed")
        return v

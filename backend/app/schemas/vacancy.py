# backend/app/schemas/vacancy.py
"""Pydantic v2 схемы для работы с вакансиями"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class VacancyStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INTERVIEWING = "interviewing"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class WorkFormat(str, Enum):
    OFFICE = "office"
    REMOTE = "remote"
    HYBRID = "hybrid"
    FLEXIBLE = "flexible"


class ExperienceLevel(str, Enum):
    NO_EXPERIENCE = "no_experience"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"
    EXPERT = "expert"


class VacancyBase(BaseModel):
    """Базовая схема вакансии"""
    title: str = Field(..., min_length=3, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    
    company_name: str = Field(default="Наша компания", max_length=255)
    location: str = Field(..., max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    
    description: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    
    requirements_mandatory: List[str] = Field(default_factory=list)
    requirements_optional: List[str] = Field(default_factory=list)


class VacancyCreate(VacancyBase):
    """Схема для создания вакансии"""
    hard_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    
    experience_years_min: float = Field(default=0, ge=0)
    experience_years_max: Optional[float] = Field(None, ge=0)
    experience_level: ExperienceLevel = ExperienceLevel.MIDDLE
    
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    work_format: WorkFormat = WorkFormat.OFFICE
    
    salary_min: Optional[int] = Field(None, gt=0)
    salary_max: Optional[int] = Field(None, gt=0)
    salary_currency: str = Field(default="RUB", max_length=10)
    
    source_file_path: Optional[str] = None
    source_gdrive_id: Optional[str] = None


class VacancyUpdate(BaseModel):
    """Схема для обновления вакансии"""
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = None
    description: Optional[str] = None
    
    hard_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    
    experience_years_min: Optional[float] = None
    experience_years_max: Optional[float] = None
    experience_level: Optional[ExperienceLevel] = None
    
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    
    status: Optional[VacancyStatus] = None
    is_urgent: Optional[bool] = None
    priority: Optional[int] = None


class VacancyResponse(VacancyBase):
    """Схема для ответа с данными вакансии"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    
    hard_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    
    experience_years_min: float = 0
    experience_years_max: Optional[float] = None
    experience_level: ExperienceLevel
    
    employment_type: EmploymentType
    work_format: WorkFormat
    
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "RUB"
    
    status: VacancyStatus
    is_urgent: bool = False
    priority: int = 0
    
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None


class VacancyWithStats(VacancyResponse):
    """Схема вакансии со статистикой"""
    views_count: int = 0
    applications_count: int = 0
    interviews_scheduled: int = 0

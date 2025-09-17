# backend/app/schemas/evaluation.py
"""Pydantic v2 схемы для работы с оценками"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any


def _empty_dict_list() -> List[Dict[str, Any]]:
    """Typed helper to provide a list of dicts."""
    return []

from datetime import datetime
from enum import Enum


class EvaluationDecision(str, Enum):
    AUTO_REJECT = "auto_reject"
    REJECT = "reject"
    RESERVE = "reserve"
    NEXT_STAGE = "next_stage"
    OFFER = "offer"
    HIRED = "hired"


class EvaluationCreate(BaseModel):
    """Схема для создания оценки"""
    interview_id: int
    candidate_id: int
    auto_evaluate: bool = True


class EvaluationUpdate(BaseModel):
    """Схема для обновления оценки (HR корректировки)"""
    model_config = ConfigDict(from_attributes=True)
    
    hr_override_decision: Optional[EvaluationDecision] = None
    hr_comments: Optional[str] = None
    hr_adjusted_score: Optional[float] = Field(None, ge=0, le=100)
    
    follow_up_questions: Optional[List[str]] = None
    areas_to_probe: Optional[List[str]] = None


class EvaluationResponse(BaseModel):
    """Схема для ответа с данными оценки"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    interview_id: int
    candidate_id: int
    
    total_score: float
    max_possible_score: float
    score_percentage: float
    
    response_rate: float
    confidence_average: Optional[float] = None
    
    decision: EvaluationDecision
    rank_in_vacancy: Optional[int] = None
    percentile: Optional[float] = None
    
    red_flags: List[Dict[str, Any]] = Field(default_factory=_empty_dict_list)
    auto_reject_reasons: List[str] = Field(default_factory=list)
    
    report_generated: bool = False
    notification_sent: bool = False
    
    created_at: datetime
    updated_at: datetime
    hr_reviewed_at: Optional[datetime] = None


class EvaluationDetail(EvaluationResponse):
    """Детальная информация об оценке"""
    scores_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    identity_match: Dict[str, Any] = Field(default_factory=dict)
    
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    
    skills_match: Dict[str, float] = Field(default_factory=dict)
    
    hr_recommendations: Optional[str] = None
    follow_up_questions: List[str] = Field(default_factory=list)
    areas_to_probe: List[str] = Field(default_factory=list)
    
    gpt_summary: Optional[str] = None
    gpt_personality_insights: Dict[str, Any] = Field(default_factory=dict)
    gpt_cultural_fit: Optional[float] = None
    
    hr_override_decision: Optional[EvaluationDecision] = None
    hr_comments: Optional[str] = None
    hr_adjusted_score: Optional[float] = None


class VacancyMatchCreate(BaseModel):
    """Схема для создания матчинга"""
    candidate_id: int
    vacancy_id: int
    run_matching: bool = True


class VacancyMatchResponse(BaseModel):
    """Схема для ответа с данными матчинга"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    candidate_id: int
    vacancy_id: int
    
    match_score: float = Field(ge=0, le=100)
    
    skills_coverage: Optional[float] = None
    experience_fit: Optional[float] = None
    salary_fit: Optional[float] = None
    
    gpt_match_reasoning: Optional[str] = None
    gpt_recommended: bool = False
    
    is_active: bool = True
    interview_scheduled: bool = False
    
    created_at: datetime
    updated_at: datetime



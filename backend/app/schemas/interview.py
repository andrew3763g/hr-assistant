# backend/app/schemas/interview.py
"""Pydantic v2 схемы для работы с интервью"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum


def _empty_dict_list() -> List[Dict[str, Any]]:
    """Typed helper to satisfy static analysis for default list of dicts."""
    return []

# class InterviewCreate(BaseModel):
#     candidate_id: int
#     vacancy_id: int


# class InterviewResponse(BaseModel):
#     id: int
#     candidate_id: int
#     vacancy_id: int
#     created_at: datetime | None = None
#
#     class Config:
#         from_attributes = True  # orm_mode (Pydantic v2)


class InterviewChatRequest(BaseModel):
    """Payload for a single interview chat turn."""
    model_config = ConfigDict(populate_by_name=True)

    interview_id: int
    message: str = Field(
        validation_alias="text",
        serialization_alias="text",
        description="Message provided by the candidate.",
    )

    @property
    def text(self) -> str:
        """Backward compatible accessor for legacy callers."""
        return self.message


class InterviewChatResponse(BaseModel):
    """Response returned after processing a chat turn."""
    model_config = ConfigDict(populate_by_name=True)

    interview_id: int
    response: str = Field(
        validation_alias="reply",
        serialization_alias="reply",
        description="Interviewer reply text.",
    )
    is_complete: bool = Field(
        default=False,
        description="Signals that the automated interview can be concluded.",
    )

class InterviewStatus(str, Enum):
    CREATED = "created"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ABANDONED = "abandoned"
    TECHNICAL_ERROR = "technical_error"
    EVALUATED = "evaluated"
    REVIEWED = "reviewed"


class QuestionType(str, Enum):
    SETUP = "setup"
    RED_FLAG = "red_flag"
    BASIC = "basic"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    SKILL = "skill"
    OPEN = "open"


class InterviewQuestionSchema(BaseModel):
    """Схема вопроса в интервью"""
    id: int
    text: str
    type: QuestionType
    category: str
    required: bool = True
    time_limit: int = 180
    order_index: int


class InterviewAnswerSchema(BaseModel):
    """Схема ответа на вопрос"""
    question_id: int
    text: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    confidence_score: Optional[float] = None
    is_answered: bool = False
    is_skipped: bool = False
    is_timeout: bool = False
    timestamp: datetime


class InterviewCreate(BaseModel):
    """Схема для создания интервью"""
    candidate_id: int
    vacancy_id: int
    questions: Optional[List[InterviewQuestionSchema]] = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InterviewStart(BaseModel):
    """Схема для начала интервью"""
    interview_token: str
    browser_info: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


class InterviewSubmitAnswer(BaseModel):
    """Схема для отправки ответа"""
    question_id: int
    audio_data: Optional[str] = None  # Base64 encoded audio
    text: Optional[str] = None
    duration_seconds: int = Field(ge=0, le=180)
    is_skip: bool = False


class InterviewResponse(BaseModel):
    """Схема для ответа с данными интервью"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    candidate_id: int
    vacancy_id: int
    
    interview_token: str
    interview_url: str
    
    status: InterviewStatus
    progress_percent: int = 0
    
    total_questions: int
    answered_questions: int = 0
    skipped_questions: int = 0
    
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class InterviewDetail(InterviewResponse):
    """Детальная информация об интервью"""
    questions_data: List[InterviewQuestionSchema]
    answers_data: Dict[str, InterviewAnswerSchema]
    
    total_duration_seconds: Optional[int] = None
    average_answer_time: Optional[float] = None
    
    red_flags_triggered: List[Dict[str, Any]] = Field(default_factory=_empty_dict_list)
    identity_verification: Dict[str, Any] = Field(default_factory=dict)
    technical_issues: List[str] = Field(default_factory=list)
    
    audio_gdrive_id: Optional[str] = None
    transcript_gdrive_id: Optional[str] = None


class InterviewFilter(BaseModel):
    """Схема для фильтрации интервью"""
    candidate_id: Optional[int] = None
    vacancy_id: Optional[int] = None
    status: Optional[InterviewStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    completed: Optional[bool] = None
    evaluated: Optional[bool] = None


class InterviewStats(BaseModel):
    """Статистика по интервью"""


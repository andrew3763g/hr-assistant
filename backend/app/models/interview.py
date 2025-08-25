# backend/app/schemas/interview.py
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from app.models.interview import InterviewStatus, InterviewType


class InterviewCreate(BaseModel):
    candidate_id: int
    vacancy_id: int
    type: InterviewType = InterviewType.SCREENING


class InterviewResponse(BaseModel):
    id: int
    candidate_id: int
    vacancy_id: int
    type: InterviewType
    status: InterviewStatus
    overall_score: Optional[float] = None
    ai_summary: Optional[str] = None
    ai_recommendation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewMessage(BaseModel):
    role: str  # 'interviewer' or 'candidate'
    content: str


class InterviewChatRequest(BaseModel):
    interview_id: int
    message: str


class InterviewChatResponse(BaseModel):
    response: str
    question_type: Optional[str] = None
    is_complete: bool = False

# -------------------
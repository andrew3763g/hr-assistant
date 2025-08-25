# backend/app/schemas/__init__.py
from .candidate import CandidateCreate, CandidateResponse
from .vacancy import VacancyCreate, VacancyResponse
from .interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewChatRequest,
    InterviewChatResponse,
    InterviewMessage
)

__all__ = [
    "CandidateCreate",
    "CandidateResponse",
    "VacancyCreate",
    "VacancyResponse",
    "InterviewCreate",
    "InterviewResponse",
    "InterviewChatRequest",
    "InterviewChatResponse",
    "InterviewMessage"
]

# -------------------
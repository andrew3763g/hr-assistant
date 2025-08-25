# backend/app/models/__init__.py
from app.models.candidate import Candidate
from app.models.vacancy import Vacancy
from app.models.interview import Interview, InterviewStatus, InterviewType
from app.models.interview_message import InterviewMessage, MessageRole

__all__ = [
    "Candidate",
    "Vacancy",
    "Interview",
    "InterviewStatus",
    "InterviewType",
    "InterviewMessage",
    "MessageRole"
]
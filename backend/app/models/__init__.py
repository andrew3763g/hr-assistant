# backend/app/models/__init__.py
from .candidate import Candidate
from .vacancy import Vacancy
from .interview import Interview
from .interview_message import InterviewMessage, MessageRole
from .evaluation import InterviewEvaluation  # если используешь
from .vacancy_match import VacancyMatch     # если используешь

__all__ = [
    "Candidate", "Vacancy", "Interview",
    "InterviewMessage", "MessageRole",
    "InterviewEvaluation", "VacancyMatch",
]

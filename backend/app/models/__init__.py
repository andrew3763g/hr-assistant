"""Модели базы данных"""

from .candidate import Candidate, CandidateStatus, Gender, EducationLevel
from .vacancy import Vacancy, VacancyStatus, EmploymentType, WorkFormat, ExperienceLevel
from .interview import Interview, InterviewStatus, InterviewQuestion, InterviewAnswer
from .interview_message import InterviewMessage
from .evaluation import Evaluation, EvaluationDecision, InterviewEvaluation
from .vacancy_match import VacancyMatch  # noqa: F401
__all__ = ['Candidate', 'Vacancy', 'Interview', 'Evaluation', 'VacancyMatch']

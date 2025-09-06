"""Модели базы данных"""

from .candidate import Candidate, CandidateStatus, Gender, EducationLevel
from .vacancy import Vacancy, VacancyStatus, EmploymentType, WorkFormat, ExperienceLevel
from .interview import Interview, InterviewStatus, InterviewQuestion, InterviewAnswer
from .evaluation import Evaluation, EvaluationDecision, VacancyMatch

__all__ = ['Candidate', 'Vacancy', 'Interview', 'Evaluation', 'VacancyMatch']

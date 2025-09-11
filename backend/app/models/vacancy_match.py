# backend/app/models/vacancy_match.py
from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from backend.app.database import Base  # <- твой Base из database.py


class VacancyMatch(Base):
    __tablename__ = "vacancy_matches"

    id = Column(Integer, primary_key=True)
    vacancy_id = Column(
        Integer,
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Integer, nullable=True)

    # Связи симметричны полям в Vacancy/Candidate (имя "matches")
    vacancy = relationship("Vacancy", back_populates="matches")
    candidate = relationship("Candidate", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("vacancy_id", "candidate_id", name="uq_vacancy_candidate"),
        Index("ix_vacancy_match_vacancy", "vacancy_id"),
        Index("ix_vacancy_match_candidate", "candidate_id"),
    )

# backend/app/models/evaluation.py
"""
Модель данных оценки кандидатов и матчинга с вакансиями
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..database import Base

class EvaluationDecision(str, enum.Enum):
    """Решения по кандидату"""
    AUTO_REJECT = "auto_reject"        # Автоматический отказ
    REJECT = "reject"                   # Отказ после оценки
    RESERVE = "reserve"                 # В резерв (места 6-10)
    NEXT_STAGE = "next_stage"          # На следующий этап (топ-5)
    OFFER = "offer"                     # Сделано предложение
    HIRED = "hired"                     # Нанят


class Evaluation(Base):
    """Модель оценки интервью"""
    __tablename__ = "evaluations"
    __table_args__ = (
        Index('ix_evaluations_interview_id', 'interview_id'),
        Index('ix_evaluations_candidate_id', 'candidate_id'),
        Index('ix_evaluations_total_score', 'total_score'),
        Index('ix_evaluations_decision', 'decision'),
    )
    
    # === Основные поля ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Связи ===
    interview_id = Column(Integer, ForeignKey('interviews.id'), unique=True, nullable=False)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    
    # === Общие баллы ===
    total_score = Column(Float, nullable=False, comment="Итоговый балл")
    max_possible_score = Column(Float, nullable=False, comment="Максимально возможный балл")
    score_percentage = Column(Float, nullable=False, comment="Процент от максимума")
    
    # === Детальные баллы (JSONB) ===
    scores_breakdown = Column(JSONB, default=dict, 
                            comment="Разбивка баллов по категориям")
    # Структура: {"basic_questions": 15, "skill_questions": 8, "confidence_bonus": 4.5, ...}
    
    # === Анализ ответов ===
    response_rate = Column(Float, nullable=False, comment="Процент отвеченных вопросов")
    confidence_average = Column(Float, nullable=True, comment="Средняя уверенность")
    
    # === Проверка личности ===
    identity_match = Column(JSONB, default=dict, 
                          comment="Результаты сверки с резюме")
    # Структура: {"name": true, "gender": true, "age": false, "mismatch_details": "..."}
    
    # === Красные флаги ===
    red_flags = Column(JSONB, default=list, 
                     comment="Список сработавших красных флагов")
    auto_reject_reasons = Column(JSONB, default=list, 
                                comment="Причины автоматического отказа")
    
    # === Сильные и слабые стороны ===
    strengths = Column(JSONB, default=list, comment="Выявленные сильные стороны")
    weaknesses = Column(JSONB, default=list, comment="Выявленные слабые стороны")
    
    # === Соответствие навыкам ===
    skills_match = Column(JSONB, default=dict, 
                        comment="Соответствие требуемым навыкам")
    # Структура: {"Python": 0.8, "SQL": 0.9, "English": 0.5, ...}
    
    # === Решение и рейтинг ===
    decision = Column(String(50), nullable=False, comment="Финальное решение")
    rank_in_vacancy = Column(Integer, nullable=True, comment="Место среди кандидатов")
    percentile = Column(Float, nullable=True, comment="Процентиль среди всех")
    
    # === Рекомендации ===
    hr_recommendations = Column(Text, nullable=True, comment="Рекомендации для HR")
    follow_up_questions = Column(JSONB, default=list, 
                               comment="Вопросы для очного интервью")
    areas_to_probe = Column(JSONB, default=list, 
                          comment="Области для углубленной проверки")
    
    # === GPT анализ ===
    gpt_summary = Column(Text, nullable=True, comment="Саммари от GPT")
    gpt_personality_insights = Column(JSONB, default=dict, 
                                    comment="Инсайты о личности от GPT")
    gpt_cultural_fit = Column(Float, nullable=True, 
                            comment="Оценка культурного соответствия")
    
    # === Отчет ===
    report_generated = Column(Boolean, default=False)
    report_gdrive_id = Column(String(255), nullable=True, comment="ID отчета в GDrive")
    notification_sent = Column(Boolean, default=False)
    notification_template = Column(String(100), nullable=True)
    
    # === Временные метки ===
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    hr_reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # === HR корректировки ===
    hr_override_decision = Column(String(50), nullable=True, comment="Решение HR")
    hr_comments = Column(Text, nullable=True)
    hr_adjusted_score = Column(Float, nullable=True)
    
    # === Связи ===
    interview = relationship("Interview", back_populates="evaluation")
    candidate = relationship("Candidate", back_populates="evaluations")


class VacancyMatch(Base):
    """Модель матчинга кандидата с вакансией"""
    __tablename__ = "vacancy_matches"
    __table_args__ = (
        UniqueConstraint('candidate_id', 'vacancy_id', name='uq_candidate_vacancy'),
        Index('ix_vacancy_matches_match_score', 'match_score'),
        Index('ix_vacancy_matches_candidate_vacancy', 'candidate_id', 'vacancy_id'),
    )
    
    # === Основные поля ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Связи ===
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    vacancy_id = Column(Integer, ForeignKey('vacancies.id'), nullable=False)
    
    # === Баллы матчинга ===
    match_score = Column(Float, nullable=False, comment="Общий балл соответствия (0-100)")
    
    # === Детали матчинга (JSONB) ===
    match_details = Column(JSONB, default=dict, comment="Детали соответствия")
    # Структура: {"skills_match": 0.8, "experience_match": 0.9, "education_match": 0.7, ...}
    
    skills_coverage = Column(Float, nullable=True, comment="Процент покрытия навыков")
    experience_fit = Column(Float, nullable=True, comment="Соответствие опыта")
    salary_fit = Column(Float, nullable=True, comment="Соответствие по зарплате")
    
    # === GPT анализ ===
    gpt_match_reasoning = Column(Text, nullable=True, comment="Обоснование матча от GPT")
    gpt_recommended = Column(Boolean, default=False, comment="Рекомендован GPT")
    
    # === Статус ===
    is_active = Column(Boolean, default=True)
    interview_scheduled = Column(Boolean, default=False)
    
    # === Временные метки ===

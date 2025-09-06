# backend/app/models/interview.py
"""
Модель данных интервью для базы данных
Хранит информацию о проведенных интервью с кандидатами
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import secrets

from ..database import Base


class InterviewStatus(str, enum.Enum):
    """Статусы интервью"""
    CREATED = "created"              # Создано, ссылка отправлена
    STARTED = "started"              # Начато кандидатом
    IN_PROGRESS = "in_progress"      # В процессе ответов на вопросы
    PAUSED = "paused"                # Приостановлено
    COMPLETED = "completed"          # Завершено кандидатом
    TIMEOUT = "timeout"              # Превышено время
    ABANDONED = "abandoned"          # Брошено кандидатом
    TECHNICAL_ERROR = "technical_error"  # Техническая ошибка
    EVALUATED = "evaluated"          # Оценено системой
    REVIEWED = "reviewed"            # Проверено HR


class Interview(Base):
    """Модель интервью"""
    __tablename__ = "interviews"
    __table_args__ = (
        Index('ix_interviews_candidate_id', 'candidate_id'),
        Index('ix_interviews_vacancy_id', 'vacancy_id'),
        Index('ix_interviews_status', 'status'),
        Index('ix_interviews_started_at', 'started_at'),
    )

    # === Основные поля ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Связи ===
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    vacancy_id = Column(Integer, ForeignKey('vacancies.id'), nullable=False)
    
    # === Информация об интервью ===
    interview_token = Column(String(255), unique=True, nullable=False, index=True, 
                           default=lambda: secrets.token_urlsafe(32),
                           comment="Уникальный токен для доступа к интервью")
    interview_url = Column(String(500), nullable=False, comment="Ссылка на интервью")
    
    # === Статус и прогресс ===
    status = Column(String(50), default=InterviewStatus.CREATED.value, nullable=False)
    progress_percent = Column(Integer, default=0, comment="Прогресс прохождения в %")
    
    # === Вопросы интервью (JSONB) ===
    questions_data = Column(JSONB, nullable=False, default=list, 
                          comment="Массив вопросов с их типами и настройками")
    # Структура: [{"id": 1, "text": "...", "type": "setup", "category": "identity", "required": true, ...}]
    
    total_questions = Column(Integer, nullable=False, comment="Общее количество вопросов")
    answered_questions = Column(Integer, default=0, comment="Количество отвеченных вопросов")
    skipped_questions = Column(Integer, default=0, comment="Количество пропущенных вопросов")
    
    # === Ответы кандидата (JSONB) ===
    answers_data = Column(JSONB, default=dict, 
                        comment="Словарь ответов {question_id: answer_data}")
    # Структура: {"1": {"text": "...", "audio_url": "...", "duration_seconds": 120, "timestamp": "..."}}
    
    # === Аудио и транскрипции ===
    audio_recordings = Column(JSONB, default=dict, 
                            comment="Ссылки на аудиозаписи ответов")
    transcriptions = Column(JSONB, default=dict, 
                          comment="Транскрипции ответов от Whisper")
    
    # === Технические данные ===
    browser_info = Column(JSONB, default=dict, comment="Информация о браузере кандидата")
    ip_address = Column(String(45), nullable=True, comment="IP адрес кандидата")
    
    # === Временные метрики ===
    total_duration_seconds = Column(Integer, nullable=True, comment="Общая длительность интервью")
    average_answer_time = Column(Float, nullable=True, comment="Среднее время ответа")
    
    # === Красные флаги и проблемы ===
    red_flags_triggered = Column(JSONB, default=list, 
                                comment="Сработавшие красные флаги")
    identity_verification = Column(JSONB, default=dict, 
                                 comment="Результаты проверки личности")
    technical_issues = Column(JSONB, default=list, 
                            comment="Технические проблемы во время интервью")
    
    # === Временные метки (timestamptz) ===
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="Когда кандидат начал")
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="Когда завершено")
    evaluated_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="Когда оценено")
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="Срок действия ссылки")
    
    # === Сохранение результатов ===
    audio_gdrive_id = Column(String(255), nullable=True, comment="ID аудио в Google Drive")
    transcript_gdrive_id = Column(String(255), nullable=True, comment="ID транскрипта в GDrive")
    
    # === Связи ===
    candidate = relationship("Candidate", back_populates="interviews")
    vacancy = relationship("Vacancy", back_populates="interviews")
    evaluation = relationship("Evaluation", back_populates="interview", uselist=False)


class InterviewQuestion(Base):
    """Модель вопроса интервью (опционально для нормализации)"""
    __tablename__ = "interview_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False)
    
    question_id = Column(Integer, nullable=False, comment="ID вопроса из базы")
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    question_category = Column(String(50), nullable=False)
    
    order_index = Column(Integer, nullable=False, comment="Порядок в интервью")
    is_required = Column(Boolean, default=True)
    time_limit_seconds = Column(Integer, default=180)
    
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class InterviewAnswer(Base):
    """Модель ответа на вопрос (опционально для нормализации)"""
    __tablename__ = "interview_answers"
    __table_args__ = (
        Index('ix_interview_answers_interview_question', 'interview_id', 'question_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False)
    question_id = Column(Integer, nullable=False)
    
    # === Ответ кандидата ===
    answer_text = Column(Text, nullable=True, comment="Транскрипция ответа")
    answer_audio_url = Column(String(500), nullable=True, comment="Ссылка на аудио")
    
    # === Метрики ответа ===
    duration_seconds = Column(Integer, nullable=True, comment="Длительность ответа")
    confidence_score = Column(Float, nullable=True, comment="Уверенность в ответе")
    
    # === Статус ответа ===
    is_answered = Column(Boolean, default=False)
    is_skipped = Column(Boolean, default=False)
    is_timeout = Column(Boolean, default=False)
    
    # === AI анализ ===
    ai_analysis = Column(JSONB, default=dict, comment="Анализ ответа от GPT")
    sentiment_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    
    answered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

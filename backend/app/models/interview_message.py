# backend/app/models/interview_message.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base


class MessageRole(str, enum.Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    SYSTEM = "system"


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)

    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Для вопросов интервьюера
    question_type = Column(String(50))  # technical, behavioral, situational
    expected_competencies = Column(JSON)  # Какие компетенции проверяем

    # Для ответов кандидата
    response_time_seconds = Column(Integer)  # Время на ответ
    word_count = Column(Integer)  # Количество слов

    # Оценка ответа (если это ответ кандидата)
    answer_score = Column(Integer)  # 0-10
    answer_evaluation = Column(JSON)  # Детальная оценка

    interview = relationship("Interview", back_populates="messages")

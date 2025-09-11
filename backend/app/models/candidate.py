# backend/app/models/candidate.py
"""
Модель данных кандидата для базы данных
Хранит информацию о кандидатах, их резюме и статусе

Что реализовано в модели:

Полная информация о кандидате:

ФИО, пол, дата рождения (критично для проверки!)
Контакты, локация, гражданство
Профессиональные данные и опыт
Образование и навыки


Критически важные поля для проверки:

gender - для сверки с интервью
birth_date/age - для проверки совершеннолетия
has_second_citizenship - красный флаг
has_red_flags - быстрая фильтрация


GPT-анализ резюме:

Саммари, сильные стороны
Подходящие роли
Уровень карьеры


Статусы кандидата - от NEW до REJECTED/APPROVED
Полезные методы:

get_full_name() - полное ФИО
is_adult() - проверка совершеннолетия
has_required_experience() - проверка опыта



🔑 Ключевые особенности:

Enum для статусов, пола, уровня образования
JSON поля для гибкого хранения навыков и языков
Связи с интервью, оценками и матчингом
"""

from sqlalchemy import Column, Integer, String, Text, Float, JSON, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from typing import Dict, List, Optional

from ..database import Base


class CandidateStatus(str, enum.Enum):
    """Статусы кандидата в системе"""
    NEW = "new"  # Новый, только загружен
    PARSED = "parsed"  # Резюме распарсено
    MATCHED = "matched"  # Подобран для вакансий
    INVITED = "invited"  # Приглашен на интервью
    INTERVIEW_SCHEDULED = "scheduled"  # Интервью назначено
    INTERVIEW_COMPLETED = "completed"  # Интервью пройдено
    EVALUATING = "evaluating"  # На оценке
    APPROVED = "approved"  # Одобрен (топ-5)
    RESERVED = "reserved"  # В резерве (6-10)
    REJECTED = "rejected"  # Отклонен
    WITHDRAWN = "withdrawn"  # Снял кандидатуру


class Gender(str, enum.Enum):
    """Пол кандидата"""
    MALE = "male"
    FEMALE = "female"
    NOT_SPECIFIED = "not_specified"


class EducationLevel(str, enum.Enum):
    """Уровень образования"""
    SECONDARY = "secondary"  # Среднее
    SECONDARY_SPECIAL = "secondary_special"  # Среднее специальное
    INCOMPLETE_HIGHER = "incomplete_higher"  # Неоконченное высшее
    BACHELOR = "bachelor"  # Бакалавр
    MASTER = "master"  # Магистр
    SPECIALIST = "specialist"  # Специалист
    PHD = "phd"  # Кандидат наук
    DOCTOR = "doctor"  # Доктор наук


class Candidate(Base):
    """Модель кандидата"""
    __tablename__ = "candidates"

    # === Основные поля ===
    id = Column(Integer, primary_key=True, index=True)

    # === Персональные данные (из резюме) ===
    last_name = Column(String(100), nullable=False, comment="Фамилия")
    first_name = Column(String(100), nullable=False, comment="Имя")
    middle_name = Column(String(100), nullable=True, comment="Отчество")

    # Пол кандидата - критически важно для проверки
    gender = Column(Enum(Gender), default=Gender.NOT_SPECIFIED, comment="Пол")

    # Дата рождения и возраст
    birth_date = Column(DateTime, nullable=True, comment="Дата рождения")
    age = Column(Integer, nullable=True, comment="Возраст")

    # === Контактная информация ===
    email = Column(String(255), unique=True, nullable=False, index=True, comment="Email")
    phone = Column(String(50), nullable=True, comment="Телефон")
    location = Column(String(255), nullable=True, comment="Город/населенный пункт")

    # === Гражданство и языки ===
    citizenship = Column(String(100), default="РФ", comment="Гражданство")
    has_second_citizenship = Column(Boolean, default=False, comment="Есть второе гражданство")
    languages = Column(JSON, default=dict, comment="Языки: {'русский': 'родной', 'английский': 'B2'}")

    # === Профессиональная информация ===
    position_desired = Column(String(255), nullable=True, comment="Желаемая должность")
    salary_expectation = Column(Integer, nullable=True, comment="Ожидаемая зарплата")

    # Опыт работы
    total_experience_years = Column(Float, nullable=True, comment="Общий стаж в годах")
    relevant_experience_years = Column(Float, nullable=True, comment="Релевантный опыт в годах")
    last_position = Column(String(255), nullable=True, comment="Последняя должность")
    last_company = Column(String(255), nullable=True, comment="Последнее место работы")

    # === Образование ===
    education_level = Column(Enum(EducationLevel), nullable=True, comment="Уровень образования")
    education_institution = Column(String(500), nullable=True, comment="Учебное заведение")
    education_speciality = Column(String(255), nullable=True, comment="Специальность")
    has_degree = Column(Boolean, default=False, comment="Есть ученая степень")

    # === Навыки и компетенции (из GPT парсинга) ===
    core_skills = Column(JSON, default=list, comment="Ключевые навыки ['Python', 'SQL', ...]")
    soft_skills = Column(JSON, default=list, comment="Soft skills ['командная работа', ...]")
    industries = Column(JSON, default=list, comment="Отрасли опыта ['банки', 'IT', ...]")
    achievements = Column(JSON, default=list, comment="Ключевые достижения")

    # === Дополнительная информация ===
    has_car = Column(Boolean, default=False, comment="Есть автомобиль")
    drivers_license = Column(String(50), nullable=True, comment="Категории прав")
    ready_for_business_trips = Column(Boolean, default=True, comment="Готов к командировкам")
    ready_for_relocation = Column(Boolean, default=False, comment="Готов к переезду")

    # === Данные о резюме ===
    resume_text = Column(Text, nullable=True, comment="Полный текст резюме")
    resume_file_path = Column(String(500), nullable=True, comment="Путь к файлу резюме")
    resume_gdrive_id = Column(String(255), nullable=True, comment="ID файла в Google Drive")

    # === GPT анализ ===
    gpt_summary = Column(Text, nullable=True, comment="Краткое саммари от GPT")
    gpt_strengths = Column(JSON, default=list, comment="Сильные стороны по мнению GPT")
    gpt_potential_roles = Column(JSON, default=list, comment="Подходящие роли по мнению GPT")
    gpt_career_level = Column(String(50), nullable=True, comment="Уровень: junior/middle/senior/lead")

    # === Статус и метаданные ===
    status = Column(Enum(CandidateStatus), default=CandidateStatus.NEW, index=True, comment="Текущий статус")

    # Флаги для быстрой фильтрации
    is_active = Column(Boolean, default=True, comment="Активен в системе")
    is_verified = Column(Boolean, default=False, comment="Данные проверены")
    has_red_flags = Column(Boolean, default=False, comment="Есть красные флаги")

    # === Временные метки ===
    created_at = Column(DateTime, default=datetime.utcnow, comment="Дата создания записи")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Дата обновления")
    parsed_at = Column(DateTime, nullable=True, comment="Дата парсинга резюме")
    last_activity_at = Column(DateTime, nullable=True, comment="Последняя активность")

    # === Связи с другими таблицами ===
    # Интервью кандидата
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")
    # Оценки кандидата
    evaluations = relationship("Evaluation", back_populates="candidate", cascade="all, delete-orphan")
    # Матчинг с вакансиями
    matches = relationship(
        "VacancyMatch",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    # === Методы модели ===

    def get_full_name(self) -> str:
        """Возвращает полное ФИО"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(filter(None, parts))

    def get_short_name(self) -> str:
        """Возвращает короткое имя (Фамилия И.О.)"""
        initials = f"{self.first_name[0]}."
        if self.middle_name:
            initials += f"{self.middle_name[0]}."
        return f"{self.last_name} {initials}"

    def get_age_from_birth_date(self) -> Optional[int]:
        """Вычисляет возраст из даты рождения"""
        if not self.birth_date:
            return None
        today = datetime.now()
        age = today.year - self.birth_date.year
        if today.month < self.birth_date.month or \
                (today.month == self.birth_date.month and today.day < self.birth_date.day):
            age -= 1
        return age

    def is_adult(self) -> bool:
        """Проверяет совершеннолетие"""
        age = self.age or self.get_age_from_birth_date()
        return age >= 18 if age else False

    def has_required_experience(self, years: float) -> bool:
        """Проверяет наличие требуемого опыта"""
        return self.total_experience_years >= years if self.total_experience_years else False

    def to_dict(self) -> Dict:
        """Преобразует модель в словарь для API"""
        return {
            "id": self.id,
            "full_name": self.get_full_name(),
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "age": self.age,
            "gender": self.gender.value if self.gender else None,
            "position_desired": self.position_desired,
            "experience_years": self.total_experience_years,
            "education_level": self.education_level.value if self.education_level else None,
            "skills": self.core_skills,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Candidate(id={self.id}, name={self.get_full_name()}, status={self.status.value})>"

    def __str__(self):
        return self.get_full_name()

# === Индексы для оптимизации запросов ===
# Создаются автоматически при миграции БД
# - email (уникальный)
# - status
# - is_active + status (составной для фильтрации активных кандидатов)
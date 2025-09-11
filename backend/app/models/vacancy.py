# backend/app/models/vacancy.py
"""
Модель данных вакансии для базы данных
Хранит информацию о вакансиях, требованиях и условиях
"""

from sqlalchemy import Column, Integer, String, Text, Float, JSON, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from typing import Dict, List, Optional

from ..database import Base


class VacancyStatus(str, enum.Enum):
    """Статусы вакансии"""
    DRAFT = "draft"  # Черновик
    ACTIVE = "active"  # Активная, идет подбор
    INTERVIEWING = "interviewing"  # Проводятся интервью
    ON_HOLD = "on_hold"  # Приостановлена
    CLOSED = "closed"  # Закрыта (нашли кандидата)
    CANCELLED = "cancelled"  # Отменена


class EmploymentType(str, enum.Enum):
    """Тип занятости"""
    FULL_TIME = "full_time"  # Полная занятость
    PART_TIME = "part_time"  # Частичная занятость
    CONTRACT = "contract"  # По договору
    INTERNSHIP = "internship"  # Стажировка
    FREELANCE = "freelance"  # Фриланс


class WorkFormat(str, enum.Enum):
    """Формат работы"""
    OFFICE = "office"  # В офисе
    REMOTE = "remote"  # Удаленная
    HYBRID = "hybrid"  # Гибридная
    FLEXIBLE = "flexible"  # По договоренности


class ExperienceLevel(str, enum.Enum):
    """Требуемый уровень опыта"""
    NO_EXPERIENCE = "no_experience"  # Без опыта
    JUNIOR = "junior"  # Junior (0-2 года)
    MIDDLE = "middle"  # Middle (2-5 лет)
    SENIOR = "senior"  # Senior (5-10 лет)
    LEAD = "lead"  # Lead (10+ лет)
    EXPERT = "expert"  # Эксперт


class Vacancy(Base):
    """Модель вакансии"""
    __tablename__ = "vacancies"

    # === Основные поля ===
    id = Column(Integer, primary_key=True, index=True)

    # === Информация о вакансии ===
    title = Column(String(255), nullable=False, index=True, comment="Название позиции")
    department = Column(String(255), nullable=True, comment="Департамент/отдел")

    # Компания и локация
    company_name = Column(String(255), default="Наша компания", comment="Название компании")
    location = Column(String(255), nullable=False, comment="Город/офис")
    address = Column(String(500), nullable=True, comment="Точный адрес офиса")

    # === Описание и требования ===
    description = Column(Text, nullable=True, comment="Полное описание вакансии")
    responsibilities = Column(JSON, default=list, comment="Должностные обязанности")

    # Требования - разделены на обязательные и желательные
    requirements_mandatory = Column(JSON, default=list, comment="Обязательные требования")
    requirements_optional = Column(JSON, default=list, comment="Желательные требования")

    # === Навыки и компетенции ===
    hard_skills = Column(JSON, default=list, comment="Hard skills ['Python', 'SQL', ...]")
    soft_skills = Column(JSON, default=list, comment="Soft skills ['командная работа', ...]")

    # Уровень требуемых навыков
    skill_levels = Column(JSON, default=dict, comment="Уровни навыков {'Python': 'advanced', ...}")

    # === Опыт и образование ===
    experience_years_min = Column(Float, default=0, comment="Минимальный опыт в годах")
    experience_years_max = Column(Float, nullable=True, comment="Максимальный опыт в годах")
    experience_level = Column(Enum(ExperienceLevel), default=ExperienceLevel.MIDDLE, comment="Уровень опыта")

    education_required = Column(String(255), nullable=True, comment="Требования к образованию")
    speciality_required = Column(String(255), nullable=True, comment="Требуемая специальность")

    # === Условия работы ===
    employment_type = Column(Enum(EmploymentType), default=EmploymentType.FULL_TIME, comment="Тип занятости")
    work_format = Column(Enum(WorkFormat), default=WorkFormat.OFFICE, comment="Формат работы")

    # Зарплатная вилка
    salary_min = Column(Integer, nullable=True, comment="Минимальная зарплата")
    salary_max = Column(Integer, nullable=True, comment="Максимальная зарплата")
    salary_currency = Column(String(10), default="RUB", comment="Валюта зарплаты")
    salary_gross = Column(Boolean, default=True, comment="Gross (true) или Net (false)")

    # === Дополнительные условия ===
    has_probation = Column(Boolean, default=True, comment="Есть испытательный срок")
    probation_months = Column(Integer, default=3, comment="Длительность испытательного срока")

    business_trips_required = Column(Boolean, default=False, comment="Требуются командировки")
    business_trips_frequency = Column(String(100), nullable=True, comment="Частота командировок")

    relocation_assistance = Column(Boolean, default=False, comment="Помощь с релокацией")

    # === Преимущества и бенефиты ===
    benefits = Column(JSON, default=list, comment="Бенефиты ['ДМС', 'обучение', ...]")

    # === Команда ===
    team_size = Column(Integer, nullable=True, comment="Размер команды")
    reports_to = Column(String(255), nullable=True, comment="Кому подчиняется")
    subordinates_count = Column(Integer, default=0, comment="Количество подчиненных")

    # === Вопросы для интервью ===
    custom_questions = Column(JSON, default=list, comment="Дополнительные вопросы для этой вакансии")
    skill_questions_template = Column(JSON, default=dict, comment="Шаблоны вопросов по навыкам")

    # === GPT анализ ===
    gpt_summary = Column(Text, nullable=True, comment="Краткое описание от GPT")
    gpt_key_requirements = Column(JSON, default=list, comment="Ключевые требования по мнению GPT")
    gpt_ideal_candidate = Column(Text, nullable=True, comment="Портрет идеального кандидата от GPT")
    gpt_interview_focus = Column(JSON, default=list, comment="На что обратить внимание на интервью")

    # === Оценочные критерии ===
    evaluation_weights = Column(JSON, default=dict, comment="Веса критериев оценки для этой вакансии")
    min_score_threshold = Column(Float, default=70.0, comment="Минимальный проходной балл")
    auto_reject_criteria = Column(JSON, default=list, comment="Дополнительные критерии автоотказа")

    # === Статистика ===
    views_count = Column(Integer, default=0, comment="Количество просмотров")
    applications_count = Column(Integer, default=0, comment="Количество откликов")
    interviews_scheduled = Column(Integer, default=0, comment="Назначено интервью")
    interviews_completed = Column(Integer, default=0, comment="Проведено интервью")

    # === Статус и метаданные ===
    status = Column(Enum(VacancyStatus), default=VacancyStatus.DRAFT, index=True, comment="Статус вакансии")
    is_urgent = Column(Boolean, default=False, comment="Срочная вакансия")
    is_hot = Column(Boolean, default=False, comment="Горячая вакансия")
    priority = Column(Integer, default=0, comment="Приоритет (чем выше, тем важнее)")

    # === Временные метки ===
    created_at = Column(DateTime, default=datetime.utcnow, comment="Дата создания")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Дата обновления")
    published_at = Column(DateTime, nullable=True, comment="Дата публикации")
    deadline_at = Column(DateTime, nullable=True, comment="Дедлайн закрытия вакансии")
    closed_at = Column(DateTime, nullable=True, comment="Дата закрытия")

    # === Источник вакансии ===
    source_file_path = Column(String(500), nullable=True, comment="Путь к исходному файлу")
    source_gdrive_id = Column(String(255), nullable=True, comment="ID файла в Google Drive")
    original_text = Column(Text, nullable=True, comment="Оригинальный текст вакансии")

    # === Ответственные ===
    hr_manager_name = Column(String(255), nullable=True, comment="ФИО HR менеджера")
    hr_manager_contact = Column(String(255), nullable=True, comment="Контакт HR менеджера")
    hiring_manager_name = Column(String(255), nullable=True, comment="ФИО нанимающего менеджера")

    # === Связи с другими таблицами ===
    # Интервью по этой вакансии
    interviews = relationship("Interview", back_populates="vacancy", cascade="all, delete-orphan")
    # Матчинг с кандидатами
    matches = relationship(
        "VacancyMatch",
        back_populates="vacancy",
        cascade="all, delete-orphan",
    )

    # === Методы модели ===

    def is_active(self) -> bool:
        """Проверяет, активна ли вакансия"""
        return self.status in [VacancyStatus.ACTIVE, VacancyStatus.INTERVIEWING]

    def is_expired(self) -> bool:
        """Проверяет, истек ли дедлайн"""
        if not self.deadline_at:
            return False
        return datetime.utcnow() > self.deadline_at

    def get_salary_range(self) -> str:
        """Возвращает зарплатную вилку как строку"""
        if not self.salary_min and not self.salary_max:
            return "По договоренности"

        if self.salary_min and self.salary_max:
            return f"{self.salary_min:,} - {self.salary_max:,} {self.salary_currency}"
        elif self.salary_min:
            return f"от {self.salary_min:,} {self.salary_currency}"
        else:
            return f"до {self.salary_max:,} {self.salary_currency}"

    def get_experience_range(self) -> str:
        """Возвращает требуемый опыт как строку"""
        if self.experience_years_min == 0 and not self.experience_years_max:
            return "Без опыта"

        if self.experience_years_min and self.experience_years_max:
            return f"{self.experience_years_min}-{self.experience_years_max} лет"
        elif self.experience_years_min:
            return f"от {self.experience_years_min} лет"
        else:
            return f"до {self.experience_years_max} лет"

    def get_all_requirements(self) -> List[str]:
        """Возвращает все требования (обязательные + желательные)"""
        all_req = list(self.requirements_mandatory or [])
        all_req.extend(self.requirements_optional or [])
        return all_req

    def get_all_skills(self) -> List[str]:
        """Возвращает все навыки (hard + soft)"""
        all_skills = list(self.hard_skills or [])
        all_skills.extend(self.soft_skills or [])
        return all_skills

    def to_dict(self) -> Dict:
        """Преобразует модель в словарь для API"""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company_name,
            "location": self.location,
            "department": self.department,
            "employment_type": self.employment_type.value if self.employment_type else None,
            "work_format": self.work_format.value if self.work_format else None,
            "experience_required": self.get_experience_range(),
            "salary_range": self.get_salary_range(),
            "skills": self.get_all_skills(),
            "requirements": self.requirements_mandatory,
            "status": self.status.value if self.status else None,
            "is_urgent": self.is_urgent,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Vacancy(id={self.id}, title={self.title}, status={self.status.value})>"

    def __str__(self):
        return f"{self.title} ({self.company_name})"

# === Индексы для оптимизации запросов ===
# Создаются автоматически при миграции БД
# - title (для поиска)
# - status (для фильтрации активных)
# - priority + status (составной для сортировки)
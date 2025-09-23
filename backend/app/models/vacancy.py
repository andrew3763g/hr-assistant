# backend/app/models/vacancy.py
"""
Модель данных вакансии для базы данных
Хранит информацию о вакансиях, требованиях и условиях
"""

from sqlalchemy import Column, Integer, String, Text, Float, JSON, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from typing import Any, Dict, List, Optional, Sequence, cast

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
    # department = Column(String(255), nullable=True, comment="Департамент/отдел")

    # Компания и локация
    # company_name = Column(String(255), default="Наша компания", comment="Название компании")
    # location = Column(String(255), nullable=False, comment="Город/офис")
    # address = Column(String(500), nullable=True, comment="Точный адрес офиса")

    # === Описание и требования ===
    description = Column(Text, nullable=True, comment="Полное описание вакансии")
    # responsibilities = Column(JSON, default=list, comment="Должностные обязанности")

    # Требования - разделены на обязательные и желательные
    # requirements_mandatory = Column(JSON, default=list, comment="Обязательные требования")
    # requirements_optional = Column(JSON, default=list, comment="Желательные требования")

    # === Навыки и компетенции ===
    # hard_skills = Column(JSON, default=list, comment="Hard skills ['Python', 'SQL', ...]")
    # soft_skills = Column(JSON, default=list, comment="Soft skills ['командная работа', ...]")

    # Уровень требуемых навыков
    # skill_levels = Column(JSON, default=dict, comment="Уровни навыков {'Python': 'advanced', ...}")

    # === Опыт и образование ===
    # experience_years_min = Column(Float, default=0, comment="Минимальный опыт в годах")
    # experience_years_max = Column(Float, nullable=True, comment="Максимальный опыт в годах")
    # experience_level = Column(Enum(ExperienceLevel), default=ExperienceLevel.MIDDLE, comment="Уровень опыта")
    #
    # education_required = Column(String(255), nullable=True, comment="Требования к образованию")
    # speciality_required = Column(String(255), nullable=True, comment="Требуемая специальность")

    # === Условия работы ===
    # employment_type = Column(Enum(EmploymentType), default=EmploymentType.FULL_TIME, comment="Тип занятости")
    # work_format = Column(Enum(WorkFormat), default=WorkFormat.OFFICE, comment="Формат работы")

    # Зарплатная вилка
    # salary_min = Column(Integer, nullable=True, comment="Минимальная зарплата")
    # salary_max = Column(Integer, nullable=True, comment="Максимальная зарплата")
    # salary_currency = Column(String(10), default="RUB", comment="Валюта зарплаты")
    # salary_gross = Column(Boolean, default=True, comment="Gross (true) или Net (false)")

    # === Дополнительные условия ===
    # has_probation = Column(Boolean, default=True, comment="Есть испытательный срок")
    # probation_months = Column(Integer, default=3, comment="Длительность испытательного срока")

    # business_trips_required = Column(Boolean, default=False, comment="Требуются командировки")
    # business_trips_frequency = Column(String(100), nullable=True, comment="Частота командировок")

    # relocation_assistance = Column(Boolean, default=False, comment="Помощь с релокацией")

    # === Преимущества и бенефиты ===
    # benefits = Column(JSON, default=list, comment="Бенефиты ['ДМС', 'обучение', ...]")

    # === Команда ===
    # team_size = Column(Integer, nullable=True, comment="Размер команды")
    # reports_to = Column(String(255), nullable=True, comment="Кому подчиняется")
    # subordinates_count = Column(Integer, default=0, comment="Количество подчиненных")

    # === Вопросы для интервью ===
    # custom_questions = Column(JSON, default=list, comment="Дополнительные вопросы для этой вакансии")
    # skill_questions_template = Column(JSON, default=dict, comment="Шаблоны вопросов по навыкам")

    # === GPT анализ ===
    # gpt_summary = Column(Text, nullable=True, comment="Краткое описание от GPT")
    # gpt_key_requirements = Column(JSON, default=list, comment="Ключевые требования по мнению GPT")
    # gpt_ideal_candidate = Column(Text, nullable=True, comment="Портрет идеального кандидата от GPT")
    # gpt_interview_focus = Column(JSON, default=list, comment="На что обратить внимание на интервью")

    # === Оценочные критерии ===
    # evaluation_weights = Column(JSON, default=dict, comment="Веса критериев оценки для этой вакансии")
    # min_score_threshold = Column(Float, default=70.0, comment="Минимальный проходной балл")
    # auto_reject_criteria = Column(JSON, default=list, comment="Дополнительные критерии автоотказа")

    # === Статистика ===
    # views_count = Column(Integer, default=0, comment="Количество просмотров")
    # applications_count = Column(Integer, default=0, comment="Количество откликов")
    # interviews_scheduled = Column(Integer, default=0, comment="Назначено интервью")
    # interviews_completed = Column(Integer, default=0, comment="Проведено интервью")

    # === Статус и метаданные ===
    # status = Column(Enum(VacancyStatus), default=VacancyStatus.DRAFT, index=True, comment="Статус вакансии")
    # is_urgent = Column(Boolean, default=False, comment="Срочная вакансия")
    # is_hot = Column(Boolean, default=False, comment="Горячая вакансия")
    # priority = Column(Integer, default=0, comment="Приоритет (чем выше, тем важнее)")

    # === Временные метки ===
    created_at = Column(DateTime, default=datetime.utcnow, comment="Дата создания")
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Дата обновления")
    # published_at = Column(DateTime, nullable=True, comment="Дата публикации")
    # deadline_at = Column(DateTime, nullable=True, comment="Дедлайн закрытия вакансии")
    # closed_at = Column(DateTime, nullable=True, comment="Дата закрытия")

    # === Источник вакансии ===
    source_file_path = Column(String(500), nullable=True, comment="Путь к исходному файлу")
    source_gdrive_id = Column(String(255), nullable=True, comment="ID файла в Google Drive")
    original_text = Column(Text, nullable=True, comment="Оригинальный текст вакансии")

    # === Ответственные ===
    # hr_manager_name = Column(String(255), nullable=True, comment="ФИО HR менеджера")
    # hr_manager_contact = Column(String(255), nullable=True, comment="Контакт HR менеджера")
    # hiring_manager_name = Column(String(255), nullable=True, comment="ФИО нанимающего менеджера")

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
        """Формирует строку с указанием диапазона компенсации."""
        salary_min = cast(Optional[int], getattr(self, "salary_min", None))
        salary_max = cast(Optional[int], getattr(self, "salary_max", None))
        currency = cast(Optional[str], getattr(self, "salary_currency", None)) or ""
        if not salary_min and not salary_max:
            return "Вилка не указана"
        if salary_min and salary_max:
            return f"{salary_min:,} - {salary_max:,} {currency}".strip()
        if salary_min:
            return f"от {salary_min:,} {currency}".strip()
        return f"до {salary_max:,} {currency}".strip()

    def get_experience_range(self) -> str:
        """Возвращает строку с требуемым опытом работы."""
        min_years = cast(Optional[float], getattr(self, "experience_years_min", None))
        max_years = cast(Optional[float], getattr(self, "experience_years_max", None))
        if not min_years and not max_years:
            return "Опыт не указан"
        if min_years and max_years:
            return f"{min_years}-{max_years} лет"
        if min_years:
            return f"от {min_years} лет"
        return f"до {max_years} лет"

    def get_all_requirements(self) -> List[str]:
        """Объединяет обязательные и желательные требования."""
        mandatory = cast(Sequence[str] | None, getattr(self, "requirements_mandatory", None)) or []
        optional = cast(Sequence[str] | None, getattr(self, "requirements_optional", None)) or []
        return list(mandatory) + list(optional)

    def get_all_skills(self) -> List[str]:
        """Комбинирует профессиональные (hard) и коммуникативные (soft) навыки."""
        hard = cast(Sequence[str] | None, getattr(self, "hard_skills", None)) or []
        soft = cast(Sequence[str] | None, getattr(self, "soft_skills", None)) or []
        return list(hard) + list(soft)

    def to_dict(self) -> Dict[str, Any]:
        """Формирует словарь ключевых данных по вакансии."""
        employment_type = cast(Optional[EmploymentType], getattr(self, "employment_type", None))
        work_format = cast(Optional[WorkFormat], getattr(self, "work_format", None))
        status = cast(Optional[VacancyStatus], getattr(self, "status", None))
        created_at = cast(Optional[datetime], getattr(self, "created_at", None))
        return {
            "id": getattr(self, "id", None),
            "title": cast(Optional[str], getattr(self, "title", None)),
            "company": cast(Optional[str], getattr(self, "company_name", None)),
            "location": cast(Optional[str], getattr(self, "location", None)),
            "department": cast(Optional[str], getattr(self, "department", None)),
            "employment_type": employment_type.value if isinstance(employment_type, EmploymentType) else None,
            "work_format": work_format.value if isinstance(work_format, WorkFormat) else None,
            "experience_required": self.get_experience_range(),
            "salary_range": self.get_salary_range(),
            "skills": self.get_all_skills(),
            "requirements": cast(Optional[Sequence[str]], getattr(self, "requirements_mandatory", None)),
            "status": status.value if isinstance(status, VacancyStatus) else None,
            "is_urgent": cast(Optional[bool], getattr(self, "is_urgent", None)),
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else None,
        }

    def __repr__(self) -> str:
        status = cast(Optional[VacancyStatus], getattr(self, "status", None))
        status_value = status.value if isinstance(status, VacancyStatus) else None
        return f"<Vacancy(id={getattr(self, 'id', None)}, title={getattr(self, 'title', None)}, status={status_value})>"

    def __str__(self) -> str:
        title = cast(Optional[str], getattr(self, "title", None)) or ""
        company = cast(Optional[str], getattr(self, "company_name", None)) or ""
        return f"{title} ({company})".strip()

# === Индексы для оптимизации запросов ===
# Создаются автоматически при миграции БД
# - title (для поиска)
# - status (для фильтрации активных)
# - priority + status (составной для сортировки)

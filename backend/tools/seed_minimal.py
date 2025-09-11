# backend/tools/seed_minimal.py
from backend.app.database import SessionLocal
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy

with SessionLocal() as db:
    vac = Vacancy(
        title="Бизнес-аналитик (антифрод)",
        location="Москва",
        description="Импорт по минимуму",
        requirements_mandatory="антифрод, ПОД/ФТ, тест-кейсы, СУБД",
        work_format="office", employment_type="full-time",
        status="open", is_active=True
    )
    db.add(vac)

    cnd = Candidate(
        last_name="Долгих", first_name="Екатерина", middle_name="Семёновна",
        email="ekaterina.dolgikh@bankmail.ru", phone="+7 (926) 987-65-43",
        location="Москва", last_position="Бизнес-аналитик", last_company="АО «Банк РЕШЕНИЕ»",
        core_skills="AS IS/TO BE, Use Case, User Story, BPMN, Jira, Confluence, SQL, Excel, Agile/Scrum",
        is_active=True
    )
    db.add(cnd)
    db.commit()
    print("seed ok")

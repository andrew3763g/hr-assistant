# tools/seed_demo.py
from backend.app.database import SessionLocal
from backend.app.models.vacancy import Vacancy
from backend.app.models.candidate import Candidate

def main():
    s = SessionLocal()

    # один раз не помешает — очищать/проверять, если нужно
    # s.query(Candidate).delete()
    # s.query(Vacancy).delete()

    vac = Vacancy(title="Data Analyst", original_text="Python/SQL/коммуникации")
    s.add(vac); s.commit(); s.refresh(vac)

    s.add_all([
        Candidate(last_name="Иванов", resume_text="Python, SQL, отчёты"),
        Candidate(last_name="Петров", resume_text="ETL, A/B, статистика"),
        Candidate(last_name="Смирнова", resume_text="BI, Excel, Python базово"),
    ])
    s.commit()
    print("Seed OK. Vacancy id:", vac.id)

if __name__ == "__main__":
    main()

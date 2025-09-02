# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os

# Импортируем database компоненты
from app.database import Base, engine

# Создаем таблицы при старте
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    yield
    # Shutdown
    print("Shutting down...")

# Создаем FastAPI приложение
app = FastAPI(
    title="HR AI Assistant",
    description="Интеллектуальный помощник для проведения собеседований",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Вместо сломанных импортов используем простые
try:
    from app.api.simple_endpoints import candidates_router, vacancies_router, interviews_router
    app.include_router(candidates_router, prefix="/api/candidates", tags=["Candidates"])
    app.include_router(vacancies_router, prefix="/api/vacancies", tags=["Vacancies"])
    app.include_router(interviews_router, prefix="/api/interviews", tags=["Interviews"])
    print("Simple endpoints loaded successfully!")
except ImportError as e:
    print(f"Could not load simple endpoints: {e}")

# # Импортируем и подключаем роутеры
# try:
#     from app.api import candidates
#     app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
#     print("Candidates router added")
# except ImportError as e:
#     print(f"Could not import candidates: {e}")
#
# try:
#     from app.api import vacancies
#     app.include_router(vacancies.router, prefix="/api/vacancies", tags=["Vacancies"])
#     print("Vacancies router added")
# except ImportError as e:
#     print(f"Could not import vacancies: {e}")
#
# try:
#     from app.api import interviews
#     app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
#     print("Interviews router added")
# except ImportError as e:
#     print(f"Could not import interviews: {e}")
#
try:
    from app.api import ai_assistant
    app.include_router(ai_assistant.router, prefix="/api/ai", tags=["AI Assistant"])
    print("AI Assistant router added")
except ImportError as e:
    print(f"Could not import ai_assistant: {e}")

# ВАЖНО: Импортируем config отдельно
try:
    from app.api import config
    app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
    print("Configuration router added successfully!")
except ImportError as e:
    print(f"ERROR: Could not import config: {e}")

# Добавь после блока с config (примерно строка 85)
try:
    from app.api import resume_upload
    app.include_router(resume_upload.router, prefix="/api/resume", tags=["Resume"])
    print("Resume upload router added successfully!")
except ImportError as e:
    print(f"ERROR: Could not import resume_upload: {e}")
# Базовые endpoints

@app.get("/")
async def root():
    return {
        "message": "HR AI Assistant API",
        "docs": "/docs",
        "health": "ok"
    }

@app.get("/api/")
async def api_root():
    return {
        "message": "API is working",
        "endpoints": {
            "candidates": "/api/candidates/",
            "vacancies": "/api/vacancies/",
            "interviews": "/api/interviews/",
            "ai": "/api/ai/",
            "config": "/api/config/"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
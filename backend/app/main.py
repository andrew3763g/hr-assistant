# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os

# Важно: импортируем после определения Base
from database import Base, engine

# Импортируем роутеры (создадим заглушки если их нет)
try:
    from app.api import candidates, interviews, vacancies, ai_assistant
    routers_available = True
except ImportError:
    routers_available = False
    print("Warning: API routers not found, starting with basic endpoints only")

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

app = FastAPI(
    title="HR AI Assistant",
    description="Интеллектуальный помощник для проведения собеседований",
    version="1.0.0",
    lifespan=lifespan
)

# CORS для работы с frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты если они доступны
if routers_available:
    app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
    app.include_router(vacancies.router, prefix="/api/vacancies", tags=["Vacancies"])
    app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
    app.include_router(ai_assistant.router, prefix="/api/ai", tags=["AI Assistant"])

@app.get("/")
async def root():
    return {
        "message": "HR AI Assistant API",
        "docs": "/docs",
        "health": "ok",
        "database_url": os.getenv("DATABASE_URL", "not set")
    }

@app.get("/api/")
async def api_root():
    return {
        "message": "API is working",
        "endpoints": {
            "candidates": "/api/candidates/",
            "vacancies": "/api/vacancies/",
            "interviews": "/api/interviews/",
            "ai": "/api/ai/"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "routers": routers_available}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
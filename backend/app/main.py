# backend/app/main.py
from dotenv import load_dotenv
load_dotenv()  # .env подхватится до любых импортов, читающих переменные окружения

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Роутеры API
from backend.app.api.imports import router as imports_router
from backend.app.api.matching import router as matching_router
from backend.app.api.vacancies import router as vacancies_router
from backend.app.api.interviews import router as interviews_router
from backend.app.api.config import router as config_router
from backend.app.api.resume_upload import router as resume_upload_router

# ВАЖНО: никаких Base.metadata.create_all — миграциями управляет Alembic

app = FastAPI(
    title="HR AI Assistant API",
    description="Интеллектуальный помощник для проведения собеседований",
    version="1.0.0",
)

# CORS (пока максимально открытый для удобства разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(imports_router,      prefix="/import",     tags=["Import"])
app.include_router(vacancies_router,   prefix="/vacancies",  tags=["Vacancies"])
app.include_router(interviews_router,  prefix="/interviews", tags=["Interviews"])
app.include_router(matching_router,    prefix="/matching",   tags=["Matching"])
app.include_router(config_router,      prefix="/config",     tags=["Config"])
app.include_router(resume_upload_router, prefix="/resume",   tags=["Resume"])

# Базовые health/doc endpoints
@app.get("/")
async def root():
    return {"message": "HR AI Assistant API", "docs": "/docs", "health": "/health"}

@app.get("/health")
async def health():
    return {"status": "ok", "openai_key_set": bool(os.getenv("OPENAI_API_KEY"))}

if __name__ == "__main__":
    # Запуск для локалки: uvicorn backend.app.main:app --reload --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)

# backend/app/main.py
from __future__ import annotations
from backend.app.api.imports import router as imports_router
from backend.app.api.matching import router as matching_router
from backend.app.api.vacancies import router as vacancies_router
from backend.app.api.interviews import router as interviews_router
from backend.app.api.config import router as config_router
from backend.app.api.resume_upload import router as resume_upload_router
from backend.app.api.admin_db import router as admin_db_router
from backend.app.config import settings
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request

import os
from dotenv import load_dotenv

# 1) .env — подхватываем максимально рано
load_dotenv()


# --- роутеры ---

app = FastAPI(
    title="HR AI Assistant API",
    description="Интеллектуальный помощник для проведения собеседований",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# статика/шаблоны (можно поменять пути под себя)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend")

API_PREFIX = "/api"

# Подключаем роутеры (без хвоста '/')
app.include_router(imports_router,
                   prefix=f"{API_PREFIX}/imports",     tags=["Imports"])
app.include_router(vacancies_router,
                   prefix=f"{API_PREFIX}/vacancies",   tags=["Vacancies"])
app.include_router(interviews_router,
                   prefix=f"{API_PREFIX}/interviews",  tags=["Interviews"])
app.include_router(matching_router,
                   prefix=f"{API_PREFIX}/matching",    tags=["Matching"])
app.include_router(config_router,
                   prefix=f"{API_PREFIX}/config",      tags=["Config"])
app.include_router(resume_upload_router,
                   prefix=f"{API_PREFIX}/resume",      tags=["Resume"])
app.include_router(admin_db_router,
                   prefix=f"{API_PREFIX}/admin/db",    tags=["Admin"])

# простая заглушка favicon (чтобы не видеть 404 в логе)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return HTMLResponse(content="", status_code=204)


@app.get("/")
async def root():
    return {"message": "HR AI Assistant API", "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "storage": settings.STORAGE_BACKEND,
    }

@app.get("/interview", response_class=HTMLResponse)
async def interview_page(request: Request):
    # пробрасываем часть настроек в шаблон
    return templates.TemplateResponse("interview.html", {"request": request, "settings": settings})

# Опционально: локальный запуск как модуля
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

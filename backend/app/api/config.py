# backend/app/api/config.py
from fastapi import APIRouter, HTTPException
import os

router = APIRouter()

# Глобальная переменная для хранения ключа в памяти
_api_key = None


@router.post("/set-api-key")
async def set_api_key(data: dict):
    """Установка OpenAI API ключа"""
    global _api_key

    openai_key = data.get("openai_key", "")
    if not openai_key.startswith('sk-'):
        raise HTTPException(status_code=400, detail="Invalid OpenAI API key format")

    _api_key = openai_key
    os.environ['OPENAI_API_KEY'] = openai_key

    masked_key = f"{openai_key[:7]}...{openai_key[-4:]}"

    return {
        "status": "success",
        "message": "API key configured successfully",
        "masked_key": masked_key
    }


@router.get("/api-key-status")
async def get_api_key_status():
    """Проверка наличия API ключа"""
    global _api_key

    has_key = _api_key is not None or os.getenv('OPENAI_API_KEY') is not None
    key_prefix = ""

    if has_key:
        key = _api_key or os.getenv('OPENAI_API_KEY')
        if key:
            key_prefix = f"{key[:7]}..."

    return {
        "has_key": has_key,
        "key_prefix": key_prefix
    }


@router.delete("/clear-api-key")
async def clear_api_key():
    """Очистка API ключа"""
    global _api_key
    _api_key = None
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    return {"status": "success", "message": "API key cleared"}
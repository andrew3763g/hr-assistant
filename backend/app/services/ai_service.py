# backend/app/services/ai_service.py
from __future__ import annotations

import json
import os
from typing import List, Dict, Any

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Клиент берём из окружения; .env уже подхватывается конфигом проекта
_client = OpenAI(api_key=OPENAI_API_KEY)


class AIInterviewer:
    """Простой HR-интервьюер: отвечает по истории диалога."""

    def __init__(self, model: str | None = None):
        self.model = model or MODEL
        self.system_prompt = (
            "You are an HR interviewer bot. Ask concise, professional questions, no more than 2 at a time. "
            "Use Russian if the candidate writes in Russian."
        )

    def chat(self, history: List[Dict[str, str]], user_text: str) -> str:
        """
        :param history: [{role: 'user'|'assistant', content: '...'}, ...]
        :param user_text: новое сообщение пользователя
        :return: ответ ассистента
        """
        messages = [{"role": "system", "content": self.system_prompt}] + history + [
            {"role": "user", "content": user_text}
        ]
        resp = _client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""


def score_match(vacancy_text: str, resume_text: str) -> Dict[str, Any]:
    """
    Черновой скоринг матчинга вакансии и резюме. Возвращает JSON со score/skills_coverage/experience_fit/salary_fit.
    """
    system = (
        "You are an HR matching assistant. Compare a vacancy and a resume and return a compact JSON with keys: "
        "score (0..100), skills_coverage (0..1), experience_fit (0..1), salary_fit (0..1). Do not add commentary."
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"VACANCY:\n{vacancy_text}\n\nRESUME:\n{resume_text}",
        },
    ]
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return {"score": 0, "skills_coverage": 0.0, "experience_fit": 0.0, "salary_fit": 0.0}

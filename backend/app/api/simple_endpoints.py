from __future__ import annotations

import os
import random
from typing import Any, Dict, List, Literal, TypedDict, cast

from fastapi import APIRouter
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

candidates_router = APIRouter()
vacancies_router = APIRouter()
interviews_router = APIRouter()


class Message(TypedDict):
    role: Literal["candidate", "interviewer"]
    content: str


class MemoryStore(TypedDict):
    candidates: Dict[int, Dict[str, Any]]
    vacancies: Dict[int, Dict[str, Any]]
    interviews: Dict[int, Dict[str, Any]]
    interview_messages: Dict[int, List[Message]]


_DATA: MemoryStore = {
    "candidates": {},
    "vacancies": {},
    "interviews": {},
    "interview_messages": {},
}


def _chat_message(role: Literal["assistant", "system", "user"], content: str) -> ChatCompletionMessageParam:
    return cast(ChatCompletionMessageParam, {"role": role, "content": content})


def _history_to_messages(history: List[Message]) -> List[ChatCompletionMessageParam]:
    messages: List[ChatCompletionMessageParam] = []
    for item in history[-10:]:
        role = "user" if item["role"] == "candidate" else "assistant"
        messages.append(_chat_message(role, item["content"]))
    return messages


@candidates_router.post("/")
async def create_candidate(data: Dict[str, Any]) -> Dict[str, Any]:
    candidate_id = random.randint(1, 10000)
    candidate = {
        "id": candidate_id,
        "email": data.get("email", "test@test.com"),
        "first_name": data.get("first_name", "Test"),
        "last_name": data.get("last_name", "User"),
        "phone": data.get("phone", ""),
    }
    _DATA["candidates"][candidate_id] = candidate
    return candidate


@candidates_router.get("/")
async def get_candidates() -> List[Dict[str, Any]]:
    return list(_DATA["candidates"].values())


@vacancies_router.post("/")
async def create_vacancy(data: Dict[str, Any]) -> Dict[str, Any]:
    vacancy_id = random.randint(1, 10000)
    vacancy = {
        "id": vacancy_id,
        "title": data.get("title", "Software Developer"),
        "level": data.get("level", "Middle"),
        "description": data.get("description", ""),
        "requirements": data.get("requirements", []),
        "skills": data.get("skills", []),
    }
    _DATA["vacancies"][vacancy_id] = vacancy
    return vacancy


@vacancies_router.get("/")
async def get_vacancies() -> List[Dict[str, Any]]:
    return list(_DATA["vacancies"].values())


@interviews_router.post("/")
async def create_interview(data: Dict[str, Any]) -> Dict[str, Any]:
    interview_id = random.randint(1, 10000)
    interview = {
        "id": interview_id,
        "candidate_id": data.get("candidate_id"),
        "vacancy_id": data.get("vacancy_id"),
        "type": data.get("type", "screening"),
        "status": "created",
    }
    _DATA["interviews"][interview_id] = interview
    _DATA["interview_messages"][interview_id] = []
    return interview


@interviews_router.get("/")
async def get_interviews() -> List[Dict[str, Any]]:
    return list(_DATA["interviews"].values())


@interviews_router.post("/chat")
async def interview_chat(data: Dict[str, Any]) -> Dict[str, Any]:
    interview_id = int(data.get("interview_id", 0))
    message = str(data.get("message", ""))

    history = _DATA["interview_messages"].setdefault(interview_id, [])
    history.append({"role": "candidate", "content": message})

    api_key = os.getenv("OPENAI_API_KEY")
    ai_response = "Спасибо за ответ. Расскажите о своём опыте работы с похожими технологиями."
    is_complete = False

    if api_key and api_key.startswith("sk-"):
        try:
            client = OpenAI(api_key=api_key)
            messages: List[ChatCompletionMessageParam] = [
                _chat_message(
                    "system",
                    (
                        "Ты проводишь техническое интервью. Задавай вопросы по очереди, не больше одного за раз. "
                        "После 5-7 вопросов заверши интервью."
                    ),
                )
            ]
            messages.extend(_history_to_messages(history))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,
                temperature=0.7,
            )
            ai_response = response.choices[0].message.content or ai_response
        except Exception as exc:  # pragma: no cover - network interaction
            print(f"OpenAI error: {exc}")
    else:
        mock_responses = [
            "Расскажите о вашем опыте работы.",
            "Какие технологии вы использовали в последнем проекте?",
            "Опишите самую сложную задачу, которую решали.",
            "Как вы подходите к отладке кода?",
            "Какие паттерны проектирования применяете?",
            "Как обеспечиваете качество кода?",
            "Опыт работы в команде?",
            "Почему хотите сменить работу?",
            "Ваши карьерные цели на ближайшие годы?",
            "Есть вопросы о нашей компании?",
            "Спасибо за интервью! Мы свяжемся с вами в течение недели.",
        ]
        msg_count = len(history)
        if msg_count >= len(mock_responses):
            ai_response = mock_responses[-1]
            is_complete = True
        else:
            index = max(0, min(msg_count - 1, len(mock_responses) - 1))
            ai_response = mock_responses[index]
            is_complete = msg_count >= 5

    history.append({"role": "interviewer", "content": ai_response})

    if not is_complete:
        is_complete = len(history) >= 10 or "свяжемся" in ai_response.lower()

    return {
        "response": ai_response,
        "is_complete": is_complete,
    }


@interviews_router.get("/{interview_id}/report")
async def get_interview_report(interview_id: int) -> Dict[str, Any]:
    messages = _DATA["interview_messages"].get(interview_id, [])
    return {
        "interview_id": interview_id,
        "messages_count": len(messages),
        "messages": messages,
        "evaluation": {
            "overall_score": 7.5,
            "recommendation": "Рекомендуем пригласить на следующий этап",
        },
    }

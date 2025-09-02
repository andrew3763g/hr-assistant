# backend/app/api/simple_endpoints.py
from fastapi import APIRouter
import random
import json

# Роутеры
candidates_router = APIRouter()
vacancies_router = APIRouter()
interviews_router = APIRouter()

# Временное хранилище в памяти
_data = {
    "candidates": {},
    "vacancies": {},
    "interviews": {},
    "interview_messages": {}
}


# CANDIDATES
@candidates_router.post("/")
async def create_candidate(data: dict):
    candidate_id = random.randint(1, 10000)
    candidate = {
        "id": candidate_id,
        "email": data.get("email", "test@test.com"),
        "first_name": data.get("first_name", "Test"),
        "last_name": data.get("last_name", "User"),
        "phone": data.get("phone", "")
    }
    _data["candidates"][candidate_id] = candidate
    return candidate


@candidates_router.get("/")
async def get_candidates():
    return list(_data["candidates"].values())


# VACANCIES
@vacancies_router.post("/")
async def create_vacancy(data: dict):
    vacancy_id = random.randint(1, 10000)
    vacancy = {
        "id": vacancy_id,
        "title": data.get("title", "Software Developer"),
        "level": data.get("level", "Middle"),
        "description": data.get("description", ""),
        "requirements": data.get("requirements", []),
        "skills": data.get("skills", [])
    }
    _data["vacancies"][vacancy_id] = vacancy
    return vacancy


@vacancies_router.get("/")
async def get_vacancies():
    return list(_data["vacancies"].values())


# INTERVIEWS
@interviews_router.post("/")
async def create_interview(data: dict):
    interview_id = random.randint(1, 10000)
    interview = {
        "id": interview_id,
        "candidate_id": data.get("candidate_id"),
        "vacancy_id": data.get("vacancy_id"),
        "type": data.get("type", "screening"),
        "status": "created"
    }
    _data["interviews"][interview_id] = interview
    _data["interview_messages"][interview_id] = []
    return interview


@interviews_router.get("/")
async def get_interviews():
    return list(_data["interviews"].values())


@interviews_router.post("/chat")
async def interview_chat(data: dict):
    import os
    interview_id = data.get("interview_id")
    message = data.get("message", "")

    # Сохраняем сообщение
    if interview_id not in _data["interview_messages"]:
        _data["interview_messages"][interview_id] = []

    _data["interview_messages"][interview_id].append({
        "role": "candidate",
        "content": message
    })

    # Генерируем ответ
    api_key = os.getenv('OPENAI_API_KEY')

    if api_key and api_key.startswith('sk-'):
        # Если есть реальный ключ - используем OpenAI
        try:
            import openai
            openai.api_key = api_key

            messages = [
                {"role": "system",
                 "content": "Ты проводишь техническое интервью. Задавай вопросы по очереди, не больше одного за раз. После 5-7 вопросов завершай интервью."},
                {"role": "user", "content": message}
            ]

            # Добавляем историю
            for msg in _data["interview_messages"][interview_id][-10:]:
                if msg["role"] == "candidate":
                    messages.append({"role": "user", "content": msg["content"]})
                else:
                    messages.append({"role": "assistant", "content": msg["content"]})

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content

        except Exception as e:
            print(f"OpenAI error: {e}")
            ai_response = "Спасибо за ответ. Расскажите о вашем опыте работы с похожими технологиями."
    else:
        # Mock ответы если нет ключа
        responses = [
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
            "Спасибо за интервью! Мы свяжемся с вами в течение недели."
        ]

        msg_count = len(_data["interview_messages"][interview_id])
        if msg_count >= len(responses):
            ai_response = responses[-1]
            is_complete = True
        else:
            ai_response = responses[min(msg_count - 1, len(responses) - 1)]
            is_complete = msg_count >= 5

    # Сохраняем ответ
    _data["interview_messages"][interview_id].append({
        "role": "interviewer",
        "content": ai_response
    })

    # Проверяем завершение
    is_complete = len(_data["interview_messages"][interview_id]) >= 10 or "свяжемся" in ai_response.lower()

    return {
        "response": ai_response,
        "is_complete": is_complete
    }


@interviews_router.get("/{interview_id}/report")
async def get_interview_report(interview_id: int):
    messages = _data["interview_messages"].get(interview_id, [])
    return {
        "interview_id": interview_id,
        "messages_count": len(messages),
        "messages": messages,
        "evaluation": {
            "overall_score": 7.5,
            "recommendation": "Рекомендуем пригласить на следующий этап"
        }
    }
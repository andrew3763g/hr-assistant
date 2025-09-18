from __future__ import annotations

import json
import os
from typing import Any, Mapping, Sequence, TypedDict, cast, Literal

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI()


class HistoryMessage(TypedDict):
    role: str
    content: str


class MatchScore(TypedDict):
    score: int
    skills_coverage: float
    experience_fit: float
    salary_fit: float


_DEFAULT_MATCH_SCORE: MatchScore = {
    "score": 0,
    "skills_coverage": 0.0,
    "experience_fit": 0.0,
    "salary_fit": 0.0,
}


HistoryInput = Mapping[str, str] | HistoryMessage


def _chat_message(role: Literal["assistant", "system", "user"], content: str) -> ChatCompletionMessageParam:
    return cast(ChatCompletionMessageParam, {"role": role, "content": content})


def _history_to_messages(history: Sequence[HistoryInput]) -> list[ChatCompletionMessageParam]:
    messages: list[ChatCompletionMessageParam] = []
    for item in history:
        role = item.get("role", "user")
        content = item.get("content", "")
        normalized_role: Literal["assistant", "system", "user"]
        if role == "assistant":
            normalized_role = "assistant"
        elif role == "system":
            normalized_role = "system"
        else:
            normalized_role = "user"
        messages.append(_chat_message(normalized_role, content))
    return messages


def _safe_float(value: Any, *, fallback: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


def _default_match_score() -> MatchScore:
    return cast(MatchScore, dict(_DEFAULT_MATCH_SCORE))


def _coerce_match_score(value: Any) -> MatchScore:
    if not isinstance(value, Mapping):
        return _default_match_score()

    mapping_value = cast(Mapping[str, object], value)
    raw_score = mapping_value.get("score", 0)
    raw_skills = mapping_value.get("skills_coverage", 0.0)
    raw_experience = mapping_value.get("experience_fit", 0.0)
    raw_salary = mapping_value.get("salary_fit", 0.0)

    score = int(_safe_float(raw_score, fallback=0.0))
    skills = _safe_float(raw_skills, fallback=0.0)
    experience = _safe_float(raw_experience, fallback=0.0)
    salary = _safe_float(raw_salary, fallback=0.0)

    result: MatchScore = {
        "score": max(0, min(100, score)),
        "skills_coverage": _clamp_ratio(skills),
        "experience_fit": _clamp_ratio(experience),
        "salary_fit": _clamp_ratio(salary),
    }
    return result


class AIInterviewer:
    """Simple HR interviewer bot that keeps the conversation short and focused."""

    def __init__(self, model: str | None = None):
        self.model = model or MODEL
        self.system_prompt = (
            "You are an HR interviewer bot. Ask concise, professional questions, no more than 2 at a time. "
            "Use Russian if the candidate writes in Russian."
        )

    def chat(self, history: Sequence[HistoryInput], user_text: str) -> str:
        conversation = [_chat_message("system", self.system_prompt)]
        conversation.extend(_history_to_messages(history))
        conversation.append(_chat_message("user", user_text))

        response = _client.chat.completions.create(
            model=self.model,
            messages=conversation,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


def score_match(vacancy_text: str, resume_text: str) -> MatchScore:
    """Score resume matching quality against a vacancy and return the structured results."""

    system = (
        "You are an HR matching assistant. Compare a vacancy and a resume and return a compact JSON with keys: "
        "score (0..100), skills_coverage (0..1), experience_fit (0..1), salary_fit (0..1). Do not add commentary."
    )

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            _chat_message("system", system),
            _chat_message("user", f"VACANCY:\n{vacancy_text}\n\nRESUME:\n{resume_text}"),
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw_content = response.choices[0].message.content or "{}"

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        return _default_match_score()

    return _coerce_match_score(parsed)
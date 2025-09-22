# -*- coding: utf-8 -*-
# backend/app/api/interviews.py
from __future__ import annotations

import contextlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TypedDict, cast

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from ..database import get_db
from backend.app.config import settings
from backend.app.models import Candidate, Vacancy
from backend.app.models.interview import Interview, InterviewStatus
from backend.app.models.interview_message import InterviewMessage, MessageRole
from backend.app.schemas.interview import (
    InterviewChatRequest,
    InterviewChatResponse,
    InterviewCreate,
    InterviewQuestionSchema,
    InterviewResponse,
)
from backend.app.services.ai_service import AIInterviewer
from backend.app.services.gdrive_service import get_storage
from backend.app.services.media_joiner import (
    ensure_ffmpeg,
    extract_wav,
    join_webm_chunks,
)

from pydantic import BaseModel

router = APIRouter()
ai_service = AIInterviewer()


class ConversationMessage(TypedDict):
    """Single utterance within the interview dialogue."""

    role: str
    content: str


class InterviewTurnResult(TypedDict):
    """Normalized AI response for an interview turn."""

    response: str
    is_complete: bool


class EvaluationPayload(TypedDict, total=False):
    """Structured result of automatic interview evaluation."""

    overall_score: float
    technical_score: float
    communication_score: float
    motivation_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    hr_comment: str


class FinalizeRequest(BaseModel):
    session_id: str


_SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


def _sanitize_component(value: str, name: str) -> str:
    filtered = "".join(ch for ch in value if ch in _SAFE_CHARS)
    if not filtered:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {name}")
    return filtered


def _media_root() -> Path:
    root = Path(settings.MEDIA_UPLOAD_ROOT).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _get_status(interview: Interview) -> str:
    return cast(str, getattr(interview, "status"))


def _set_status(interview: Interview, status: InterviewStatus) -> None:
    setattr(interview, "status", status.value)


def _set_timestamp(interview: Interview, attr: str) -> None:
    setattr(interview, attr, datetime.utcnow())


def _normalize_questions(
    source: Optional[Sequence[InterviewQuestionSchema]],
    vacancy: Optional[Vacancy],
) -> List[Dict[str, Any]]:
    if source:
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(source):
            data = cast(Dict[str, Any], item.model_dump())
            data.setdefault("order_index", idx)
            normalized.append(data)
        return normalized
    return _generate_questions(vacancy)


def _generate_questions(vacancy: Optional[Vacancy]) -> List[Dict[str, Any]]:
    generator = getattr(ai_service, "generate_interview_questions", None)
    if callable(generator):
        result = generator(vacancy)  # type: ignore[arg-type, call-arg]
        if isinstance(result, list):
            normalized: List[Dict[str, Any]] = []
            for idx, item in enumerate(result):
                if hasattr(item, "model_dump"):
                    data = cast(Dict[str, Any], item.model_dump())
                elif isinstance(item, dict):
                    data = dict(item)
                else:
                    continue
                data.setdefault("order_index", idx)
                normalized.append(data)
            if normalized:
                return normalized
    title = getattr(vacancy, "title", None)
    role_phrase = f"на позицию {title}" if title else "на целевую позицию"
    questions = [
        f"Для начала расскажите, пожалуйста, кратко о себе и текущих задачах, чтобы мы лучше понимали ваш контекст {role_phrase}.",
        "Опишите последний значимый проект: какова была ваша роль, состав команды и основной технологический стек?",
        "Какие языки программирования, фреймворки, базы данных и облачные сервисы вы применяете чаще всего и по каким критериям их выбираете?",
        "Как вы организуете взаимодействие с командой и как обычно решаете рабочие разногласия?",
        "Что для вас сейчас наиболее важно при выборе нового работодателя, формата работы и условий сотрудничества?",
        "Какие вопросы у вас есть к нам и каких ожиданий по предложению вы придерживаетесь?",
    ]
    return [
        {
            "id": idx + 1,
            "text": question,
            "type": "open",
            "category": "general",
            "required": True,
            "order_index": idx,
        }
        for idx, question in enumerate(questions)
    ]


def _conduct_turn(
    history: Sequence[ConversationMessage],
    message: str,
    vacancy: Optional[Vacancy],
) -> InterviewTurnResult:
    handler = getattr(ai_service, "conduct_interview_turn", None)
    if callable(handler):
        result = handler(history, message, vacancy)  # type: ignore[arg-type, call-arg]
        if isinstance(result, dict):
            response = str(result.get("response", "")).strip()
            if response:
                return InterviewTurnResult(
                    response=response,
                    is_complete=bool(result.get("is_complete")),
                )
    follow_up_base = "Спасибо за ответ. "
    normalized_length = len(message.strip())
    if normalized_length < 60:
        prompts = [
            "Могли бы вы уточнить конкретный вклад и результаты, чтобы нам было легче оценить ваш опыт?",
            "Поделитесь, пожалуйста, примером задачи и инструментов, с которыми вы работали в этой ситуации.",
            "Расскажите, какие решения приняли именно вы и что помогло вам добиться результата?",
            "Буду признателен, если опишете детали: цели проекта, масштабы и взаимодействие с командой.",
        ]
    else:
        prompts = [
            "Перейдём к следующему вопросу и обсудим ваш технический стек подробнее.",
            "Давайте теперь поговорим о командном взаимодействии и вашем вкладе в процессы.",
            "Предлагаю перейти к вопросам о мотивации и ожиданиях от новой роли.",
        ]
    prompt = prompts[len(history) % len(prompts)]
    follow_up = follow_up_base + prompt
    is_complete = len(history) >= 8
    return InterviewTurnResult(response=follow_up, is_complete=is_complete)


def _evaluate_interview(
    history: Sequence[ConversationMessage],
    vacancy: Optional[Vacancy],
) -> EvaluationPayload:
    evaluator = getattr(ai_service, "evaluate_interview", None)
    if callable(evaluator):
        result = evaluator(history, vacancy)  # type: ignore[arg-type, call-arg]
        if isinstance(result, dict):
            payload: EvaluationPayload = EvaluationPayload()
            for key in ("overall_score", "technical_score", "communication_score", "motivation_score"):
                value = result.get(key)
                if isinstance(value, (int, float)):
                    payload[key] = float(value)
            for key in ("strengths", "weaknesses"):
                value = result.get(key)
                if isinstance(value, list):
                    payload[key] = [str(item) for item in value]
            recommendation = result.get("recommendation")
            if isinstance(recommendation, str):
                payload["recommendation"] = recommendation
            comment = result.get("hr_comment") or result.get("summary")
            if isinstance(comment, str):
                payload["hr_comment"] = comment
            if payload:
                return payload
    answered = sum(1 for m in history if m["role"] == "user")
    base_score = float(min(100, answered * 15))
    return EvaluationPayload(
        overall_score=base_score,
        technical_score=base_score * 0.8,
        communication_score=base_score * 0.85,
        motivation_score=base_score * 0.9,
        strengths=[
            "чёткая структура ответов",
            "релевантный опыт с современными веб-сервисами",
            "глубокое понимание командного взаимодействия",
            "инициативность в предложении решений",
        ],
        weaknesses=[
            "недостаточно примеров нагрузочного тестирования",
            "неуверенность в миграциях на базе Alembic",
            "ограниченное покрытие инструментов мониторинга",
        ],
        recommendation="Рекомендую пригласить на следующий этап технического интервью.",
        hr_comment=(
            "Кандидат уверенно описывает ключевые проекты и роли. "
            "Технические ответы структурированы, но часть стека требует уточнения. "
            "Мотивация и ожидания по условиям прозрачны и совпадают с возможностями команды."
        ),
    )


@router.post("/", response_model=InterviewResponse)
def create_interview(interview: InterviewCreate, db: Session = Depends(get_db)):
    """Создаёт интервью, сохраняет базовый набор вопросов и возвращает карточку интервью."""
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    expires_at = datetime.utcnow() + timedelta(days=interview.expires_in_days)
    db_interview = Interview(
        candidate_id=interview.candidate_id,
        vacancy_id=interview.vacancy_id,
    )
    _set_status(db_interview, InterviewStatus.CREATED)
    setattr(db_interview, "expires_at", expires_at)

    questions = _normalize_questions(interview.questions, vacancy)
    setattr(db_interview, "questions_data", questions)
    setattr(db_interview, "total_questions", len(questions))

    db.add(db_interview)
    db.flush()

    if not getattr(db_interview, "interview_url", None):
        token = cast(str, getattr(db_interview, "interview_token", ""))
        setattr(db_interview, "interview_url", f"/interviews/{token}" if token else "")

    db.commit()
    db.refresh(db_interview)

    return db_interview


@router.get("/", response_model=List[InterviewResponse])
def get_interviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Возвращает список интервью с пагинацией по параметрам skip и limit."""
    interviews = db.query(Interview).offset(skip).limit(limit).all()
    return interviews


@router.post("/chat", response_model=InterviewChatResponse)
def interview_chat(request: InterviewChatRequest, db: Session = Depends(get_db)):
    """Записывает сообщение кандидата, генерирует ответ интервьюера и обновляет статус интервью."""
    interview = db.query(Interview).filter(Interview.id == request.interview_id).first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()

    messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.interview_id == interview.id)
        .order_by(InterviewMessage.timestamp)
        .all()
    )

    conversation_history: List[ConversationMessage] = []
    for msg in messages:
        role_value = cast(MessageRole, getattr(msg, "role"))
        role = "assistant" if role_value == MessageRole.INTERVIEWER else "user"
        content = cast(str, getattr(msg, "content"))
        conversation_history.append({"role": role, "content": content})

    user_message = getattr(request, "message", request.text)
    conversation_history.append({"role": "user", "content": user_message})

    candidate_msg = InterviewMessage(
        interview_id=interview.id,
        role=MessageRole.CANDIDATE,
        content=user_message,
    )
    db.add(candidate_msg)

    ai_response = _conduct_turn(conversation_history, user_message, vacancy)
    conversation_history.append({"role": "assistant", "content": ai_response["response"]})

    interviewer_msg = InterviewMessage(
        interview_id=interview.id,
        role=MessageRole.INTERVIEWER,
        content=ai_response["response"],
    )
    db.add(interviewer_msg)

    if _get_status(interview) == InterviewStatus.CREATED.value:
        _set_status(interview, InterviewStatus.IN_PROGRESS)
        _set_timestamp(interview, "started_at")

    if ai_response["is_complete"]:
        _set_status(interview, InterviewStatus.COMPLETED)
        _set_timestamp(interview, "completed_at")

        evaluation = _evaluate_interview(conversation_history, vacancy)
        for source_key, target_attr in (
            ("overall_score", "overall_score"),
            ("technical_score", "technical_score"),
            ("communication_score", "communication_score"),
            ("motivation_score", "motivation_score"),
            ("strengths", "strengths"),
            ("weaknesses", "weaknesses"),
            ("recommendation", "ai_recommendation"),
            ("hr_comment", "ai_summary"),
        ):
            value = evaluation.get(source_key)
            if value is not None:
                setattr(interview, target_attr, value)

    db.commit()

    return InterviewChatResponse(
        interview_id=cast(int, getattr(interview, "id")),
        response=ai_response["response"],
        is_complete=ai_response["is_complete"],
    )


@router.get("/{interview_id}/report")
def get_interview_report(interview_id: int, db: Session = Depends(get_db)):
    """Возвращает итоговый отчёт по интервью с оценками и аналитикой."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()

    return {
        "interview": interview,
        "candidate": candidate,
        "vacancy": vacancy,
        "scores": {
            "overall": getattr(interview, "overall_score", None),
            "technical": getattr(interview, "technical_score", None),
            "communication": getattr(interview, "communication_score", None),
            "motivation": getattr(interview, "motivation_score", None),
        },
        "analysis": {
            "strengths": getattr(interview, "strengths", None),
            "weaknesses": getattr(interview, "weaknesses", None),
            "recommendation": getattr(interview, "ai_recommendation", None),
            "summary": getattr(interview, "ai_summary", None),
        },
    }


@router.post("/upload/chunk")
async def upload_chunk(
    session_id: str = Form(...),
    kind: str = Form(...),
    index: int = Form(...),
    chunk: UploadFile = File(...),
):
    """Принимает и сохраняет отдельный медиа-фрагмент интервью."""
    safe_session = _sanitize_component(session_id, "session_id")
    safe_kind = _sanitize_component(kind, "kind")

    root = _media_root()
    chunk_dir = root / safe_session / safe_kind
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunk_path = chunk_dir / f"{int(index):06d}.webm"

    with chunk_path.open("wb") as buffer:
        while True:
            data = await chunk.read(1024 * 1024)
            if not data:
                break
            buffer.write(data)

    await chunk.close()

    return {
        "ok": True,
        "stored": str(chunk_path.relative_to(root)),
    }


@router.post("/upload/finalize")
def finalize_upload(payload: FinalizeRequest = Body(...)):
    """Объединяет загруженные фрагменты, формирует итоговые файлы и загружает их в хранилище."""
    safe_session = _sanitize_component(payload.session_id, "session_id")

    root = _media_root()
    session_dir = root / safe_session
    if not session_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    ffmpeg_bin = settings.FFMPEG_BIN or "ffmpeg"
    ffmpeg_ready = ensure_ffmpeg(ffmpeg_bin)
    if not ffmpeg_ready:
        message = f"FFmpeg binary '{ffmpeg_bin}' is not available"
        if settings.EXTRACT_WAV:
            raise RuntimeError(f"{message}; cannot extract WAV while EXTRACT_WAV=1.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)

    storage = get_storage()

    artifacts: Dict[str, Dict[str, Optional[str]]] = {}
    processed_dirs: List[Path] = []

    for kind_dir in sorted(p for p in session_dir.iterdir() if p.is_dir()):
        chunk_files = sorted(kind_dir.glob("*.webm"))
        if not chunk_files:
            continue

        final_webm = kind_dir / "final.webm"
        if final_webm.exists():
            final_webm.unlink()

        join_webm_chunks(chunk_files, final_webm, ffmpeg_bin=ffmpeg_bin)

        wav_path: Optional[Path] = None
        if settings.EXTRACT_WAV:
            wav_path = kind_dir / "final.wav"
            if wav_path.exists():
                wav_path.unlink()
            extract_wav(final_webm, wav_path, ffmpeg_bin=ffmpeg_bin)

        kind_key = kind_dir.name
        video_data = final_webm.read_bytes()
        video_name = f"{safe_session}_{kind_key}.webm"
        video_link = storage.upload(video_data, video_name, folder_key="VIDEO")

        audio_link: Optional[str] = None
        if wav_path and wav_path.exists():
            audio_data = wav_path.read_bytes()
            audio_name = f"{safe_session}_{kind_key}.wav"
            audio_link = storage.upload(audio_data, audio_name, folder_key="AUDIO")

        artifacts[kind_key] = {
            "webm": video_link,
            "wav": audio_link,
        }

        processed_dirs.append(kind_dir)

    if not artifacts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No media chunks found")

    for directory in processed_dirs:
        shutil.rmtree(directory, ignore_errors=True)

    with contextlib.suppress(OSError):
        session_dir.rmdir()

    return {
        "session_id": safe_session,
        "artifacts": artifacts,
    }


@router.get("/admin/check/ffmpeg")
def admin_check_ffmpeg():
    """Проверяет доступность установленного бинарника FFmpeg."""
    ffmpeg_bin = settings.FFMPEG_BIN or "ffmpeg"
    if ensure_ffmpeg(ffmpeg_bin):
        return {"ok": True, "bin": ffmpeg_bin}
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"ok": False, "bin": ffmpeg_bin},
    )


# CHANGELOG: восстановлены русскоязычные формулировки вопросов, реплик и оценок, добавлены описания эндпоинтов.

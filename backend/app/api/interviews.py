
# backend/app/api/interviews.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, TypedDict, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
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
    title = getattr(vacancy, "title", None) or "???????"
    questions = [
        f"?????????? ?????? ? ????? ?????, ??????????? ???? {title}.",
        "????? ?????????? ? ????????? ??????? ?? ???????? ??????????",
        "????? ???????? ? ??? ?? ??????? ? ?????????????",
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
    follow_up_base = "??????? ?? ?????. "
    lowered = message.lower()
    if "???" in lowered or "project" in lowered:
        follow_up = follow_up_base + "?????????? ????????? ? ????????? ???????, ??????? ?? ?????????."
    else:
        follow_up = follow_up_base + "?????? ???????? ??????, ?????????????? ??? ?????"
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
        strengths=["????????? ?????????????? ? ????????????"],
        weaknesses=["????? ?????? ?????????? ? ????????"],
        recommendation="???????? ????? ???????? ? ???????? ???????????? ???????????.",
        hr_comment="????????????? ??????: ??? ?????? ??????????? ???????, ??? ???? ?????.",
    )


@router.post("/", response_model=InterviewResponse)
def create_interview(interview: InterviewCreate, db: Session = Depends(get_db)):
    """??????? ????? ?????? ???????? ? ?????????????? ????????? ???????."""
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
    """?????????? ?????? ????????."""
    interviews = db.query(Interview).offset(skip).limit(limit).all()
    return interviews


@router.post("/chat", response_model=InterviewChatResponse)
def interview_chat(request: InterviewChatRequest, db: Session = Depends(get_db)):
    """???????????? ??? ??????? ????? ?????????? ? ????????????."""
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
    """?????????? ?????????????? ????? ?? ????????."""
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

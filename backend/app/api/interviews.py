# backend/app/api/interviews.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Interview, Candidate, Vacancy, InterviewMessage, MessageRole
from ..schemas.interview import InterviewCreate, InterviewResponse, InterviewChatRequest, InterviewChatResponse
from ..services.ai_service import AIInterviewer
from datetime import datetime

router = APIRouter()
ai_service = AIInterviewer()


@router.post("/", response_model=InterviewResponse)
def create_interview(interview: InterviewCreate, db: Session = Depends(get_db)):
    """Создание нового интервью"""
    # Проверяем существование кандидата и вакансии
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    # Создаем интервью
    db_interview = Interview(**interview.dict())
    db_interview.status = "scheduled"
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)

    # Генерируем начальные вопросы
    questions = ai_service.generate_interview_questions(vacancy)
    db_interview.questions_asked = questions
    db.commit()

    return db_interview


@router.get("/", response_model=List[InterviewResponse])
def get_interviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получение списка интервью"""
    interviews = db.query(Interview).offset(skip).limit(limit).all()
    return interviews


@router.post("/chat", response_model=InterviewChatResponse)
def interview_chat(request: InterviewChatRequest, db: Session = Depends(get_db)):
    """Чат во время интервью"""
    # Получаем интервью
    interview = db.query(Interview).filter(Interview.id == request.interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Получаем вакансию
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()

    # Получаем историю сообщений
    messages = db.query(InterviewMessage).filter(
        InterviewMessage.interview_id == interview.id
    ).order_by(InterviewMessage.timestamp).all()

    # Формируем историю для AI
    conversation_history = []
    for msg in messages:
        role = "assistant" if msg.role == MessageRole.INTERVIEWER else "user"
        conversation_history.append({"role": role, "content": msg.content})

    # Сохраняем сообщение кандидата
    candidate_msg = InterviewMessage(
        interview_id=interview.id,
        role=MessageRole.CANDIDATE,
        content=request.message
    )
    db.add(candidate_msg)

    # Получаем ответ AI
    ai_response = ai_service.conduct_interview_turn(
        conversation_history,
        request.message,
        vacancy
    )

    # Сохраняем ответ интервьюера
    interviewer_msg = InterviewMessage(
        interview_id=interview.id,
        role=MessageRole.INTERVIEWER,
        content=ai_response["response"]
    )
    db.add(interviewer_msg)

    # Обновляем статус интервью
    if interview.status == "scheduled":
        interview.status = "in_progress"
        interview.started_at = datetime.utcnow()

    if ai_response["is_complete"]:
        interview.status = "completed"
        interview.completed_at = datetime.utcnow()

        # Оцениваем интервью
        evaluation = ai_service.evaluate_interview(conversation_history, vacancy)
        interview.overall_score = evaluation.get("overall_score", 0)
        interview.technical_score = evaluation.get("technical_score", 0)
        interview.communication_score = evaluation.get("communication_score", 0)
        interview.motivation_score = evaluation.get("motivation_score", 0)
        interview.strengths = evaluation.get("strengths", [])
        interview.weaknesses = evaluation.get("weaknesses", [])
        interview.ai_recommendation = evaluation.get("recommendation", "")
        interview.ai_summary = evaluation.get("hr_comment", "")

    db.commit()

    return InterviewChatResponse(
        response=ai_response["response"],
        is_complete=ai_response["is_complete"]
    )


@router.get("/{interview_id}/report")
def get_interview_report(interview_id: int, db: Session = Depends(get_db)):
    """Получение отчета по интервью"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()

    return {
        "interview": interview,
        "candidate": candidate,
        "vacancy": vacancy,
        "scores": {
            "overall": interview.overall_score,
            "technical": interview.technical_score,
            "communication": interview.communication_score,
            "motivation": interview.motivation_score
        },
        "analysis": {
            "strengths": interview.strengths,
            "weaknesses": interview.weaknesses,
            "recommendation": interview.ai_recommendation,
            "summary": interview.ai_summary
        }
    }
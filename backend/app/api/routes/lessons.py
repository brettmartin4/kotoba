from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from app.core.db import get_engine
from app.services.lesson_service import (
    LessonSessionNotFoundError,
    NoEligibleItemsError,
    SourceNotFoundError,
    complete_lesson_session,
    get_lessons_available,
    record_lesson_answer,
    start_lesson_session,
)

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


class StartLessonRequest(BaseModel):
    source_id: int


class LessonAnswerRequest(BaseModel):
    item_id: int
    prompt_type: Literal["meaning", "japanese"]
    submitted_answer: str


@router.get("/available")
def lessons_available(engine: Engine = Depends(get_engine)):
    return get_lessons_available(engine)


@router.post("/start")
def start(body: StartLessonRequest, engine: Engine = Depends(get_engine)):
    try:
        return start_lesson_session(engine, body.source_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except NoEligibleItemsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{session_id}/answer")
def answer(session_id: int, body: LessonAnswerRequest, engine: Engine = Depends(get_engine)):
    try:
        return record_lesson_answer(
            engine, session_id, body.item_id, body.prompt_type, body.submitted_answer
        )
    except LessonSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{session_id}/complete")
def complete(session_id: int, engine: Engine = Depends(get_engine)):
    try:
        return complete_lesson_session(engine, session_id)
    except LessonSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from app.core.db import get_engine
from app.services.review_service import (
    NoDueItemsError,
    ReviewSessionNotFoundError,
    complete_review_session,
    get_reviews_available,
    record_review_answer,
    start_review_session,
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewAnswerRequest(BaseModel):
    item_id: int
    prompt_type: Literal["meaning", "japanese"]
    submitted_answer: str


@router.get("/available")
def reviews_available(engine: Engine = Depends(get_engine)):
    return get_reviews_available(engine)


@router.post("/start")
def start(engine: Engine = Depends(get_engine)):
    try:
        return start_review_session(engine)
    except NoDueItemsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{session_id}/answer")
def answer(session_id: int, body: ReviewAnswerRequest, engine: Engine = Depends(get_engine)):
    try:
        return record_review_answer(
            engine, session_id, body.item_id, body.prompt_type, body.submitted_answer
        )
    except ReviewSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{session_id}/complete")
def complete(session_id: int, engine: Engine = Depends(get_engine)):
    try:
        return complete_review_session(engine, session_id)
    except ReviewSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

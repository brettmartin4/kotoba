from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.engine import Engine

from app.core.db import get_engine
from app.services.settings_service import InvalidSettingValueError, get_daily_lesson_cap, set_daily_lesson_cap

router = APIRouter(prefix="/api/settings", tags=["settings"])


class UpdateSettingsRequest(BaseModel):
    daily_lesson_cap: int

    @field_validator("daily_lesson_cap")
    @classmethod
    def at_least_one(cls, value: int) -> int:
        if value < 1:
            raise ValueError("daily_lesson_cap must be at least 1")
        return value


@router.get("")
def get_settings(engine: Engine = Depends(get_engine)):
    with engine.connect() as conn:
        return {"daily_lesson_cap": get_daily_lesson_cap(conn)}


@router.patch("")
def patch_settings(body: UpdateSettingsRequest, engine: Engine = Depends(get_engine)):
    with engine.begin() as conn:
        try:
            new_value = set_daily_lesson_cap(conn, body.daily_lesson_cap)
        except InvalidSettingValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"daily_lesson_cap": new_value}

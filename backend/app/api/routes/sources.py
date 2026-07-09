from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.engine import Engine

from app.core.db import get_engine
from app.services.dashboard_service import rename_source
from app.services.level_service import get_sources_overview

router = APIRouter(prefix="/api/sources", tags=["sources"])


class RenameSourceRequest(BaseModel):
    display_name: str

    @field_validator("display_name")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("display_name must not be blank")
        return stripped


@router.get("")
def list_sources(engine: Engine = Depends(get_engine)):
    with engine.connect() as conn:
        return get_sources_overview(conn)


@router.patch("/{source_id}")
def patch_source(source_id: int, body: RenameSourceRequest, engine: Engine = Depends(get_engine)):
    with engine.begin() as conn:
        updated = rename_source(conn, source_id, body.display_name)
    if updated is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return updated

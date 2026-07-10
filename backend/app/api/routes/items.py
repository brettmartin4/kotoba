from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.engine import Engine

from app.core.db import get_engine
from app.services.item_service import (
    CannotDeleteImportedMeaningError,
    ItemNotFoundError,
    SynonymNotFoundError,
    add_synonym,
    delete_synonym,
    get_item_page,
    list_items,
    update_notes,
)

router = APIRouter(prefix="/api/items", tags=["items"])


class AddSynonymRequest(BaseModel):
    meaning: str

    @field_validator("meaning")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("meaning must not be blank")
        return stripped


class NotesUpdateRequest(BaseModel):
    note_text: Optional[str] = None
    mnemonic_text: Optional[str] = None


@router.get("")
def get_items(
    search: Optional[str] = None,
    source_id: Optional[int] = None,
    item_type: Optional[str] = None,
    srs_group: str = "all",
    active_filter: str = "active_only",
    engine: Engine = Depends(get_engine),
):
    with engine.connect() as conn:
        return list_items(
            conn,
            search=search,
            source_id=source_id,
            item_type=item_type,
            srs_group=srs_group,
            active_filter=active_filter,
        )


@router.get("/{item_id}")
def get_item(item_id: int, engine: Engine = Depends(get_engine)):
    with engine.connect() as conn:
        detail = get_item_page(conn, item_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return detail


@router.patch("/{item_id}/notes")
def patch_notes(item_id: int, body: NotesUpdateRequest, engine: Engine = Depends(get_engine)):
    updates = body.model_dump(exclude_unset=True)
    with engine.begin() as conn:
        result = update_notes(conn, item_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.post("/{item_id}/synonyms")
def post_synonym(item_id: int, body: AddSynonymRequest, engine: Engine = Depends(get_engine)):
    try:
        with engine.begin() as conn:
            return add_synonym(conn, item_id, body.meaning)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{item_id}/synonyms/{synonym_id}")
def delete_synonym_route(item_id: int, synonym_id: int, engine: Engine = Depends(get_engine)):
    try:
        with engine.begin() as conn:
            delete_synonym(conn, item_id, synonym_id)
    except SynonymNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CannotDeleteImportedMeaningError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return {"deleted": True}

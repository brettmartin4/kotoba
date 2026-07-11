from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from app.core.config import get_wordbank_folder
from app.core.db import get_engine
from app.services.import_service import (
    AlreadyResolvedError,
    ImportRunItemNotFoundError,
    InvalidMergeTargetError,
    ItemNotFoundError,
    SourceRelationshipNotFoundError,
    approve_change,
    get_import_run_detail,
    get_import_runs,
    get_pending_changes,
    get_pending_duplicates,
    keep_separate_duplicate,
    merge_duplicate,
    reject_change,
    run_import,
    skip_duplicate,
)

router = APIRouter(prefix="/api/import", tags=["import"])

_ERROR_STATUS_CODES = {
    ImportRunItemNotFoundError: 404,
    ItemNotFoundError: 404,
    AlreadyResolvedError: 409,
    SourceRelationshipNotFoundError: 409,
    InvalidMergeTargetError: 400,
}
_HANDLED_ERRORS = tuple(_ERROR_STATUS_CODES.keys())


def _run_import_action(fn, *args):
    try:
        return fn(*args)
    except _HANDLED_ERRORS as exc:
        raise HTTPException(status_code=_ERROR_STATUS_CODES[type(exc)], detail=str(exc)) from exc


class MergeDuplicateRequest(BaseModel):
    target_item_id: int


@router.post("/refresh")
def refresh(
    engine: Engine = Depends(get_engine),
    wordbank_folder: Path = Depends(get_wordbank_folder),
):
    return run_import(engine, wordbank_folder)


@router.get("/runs")
def list_runs(engine: Engine = Depends(get_engine)):
    return get_import_runs(engine)


@router.get("/runs/{run_id}")
def run_detail(run_id: int, engine: Engine = Depends(get_engine)):
    detail = get_import_run_detail(engine, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Import run not found")
    return detail


@router.get("/duplicates/pending")
def duplicates_pending(engine: Engine = Depends(get_engine)):
    return get_pending_duplicates(engine)


@router.get("/changes/pending")
def changes_pending(engine: Engine = Depends(get_engine)):
    return get_pending_changes(engine)


@router.post("/duplicates/{import_run_item_id}/merge")
def merge(import_run_item_id: int, body: MergeDuplicateRequest, engine: Engine = Depends(get_engine)):
    return _run_import_action(merge_duplicate, engine, import_run_item_id, body.target_item_id)


@router.post("/duplicates/{import_run_item_id}/keep-separate")
def keep_separate(import_run_item_id: int, engine: Engine = Depends(get_engine)):
    return _run_import_action(keep_separate_duplicate, engine, import_run_item_id)


@router.post("/duplicates/{import_run_item_id}/skip")
def skip(import_run_item_id: int, engine: Engine = Depends(get_engine)):
    return _run_import_action(skip_duplicate, engine, import_run_item_id)


@router.post("/changes/{import_run_item_id}/approve")
def approve(import_run_item_id: int, engine: Engine = Depends(get_engine)):
    return _run_import_action(approve_change, engine, import_run_item_id)


@router.post("/changes/{import_run_item_id}/reject")
def reject(import_run_item_id: int, engine: Engine = Depends(get_engine)):
    return _run_import_action(reject_change, engine, import_run_item_id)

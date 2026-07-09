from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Engine

from app.core.config import get_wordbank_folder
from app.core.db import get_engine
from app.services.import_service import get_import_run_detail, get_import_runs, run_import

router = APIRouter(prefix="/api/import", tags=["import"])


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

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Engine

from app.core.db import get_engine
from app.services.dashboard_service import get_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(engine: Engine = Depends(get_engine)):
    return get_dashboard(engine)

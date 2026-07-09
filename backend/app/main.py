from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.imports import router as imports_router
from app.api.routes.sources import router as sources_router
from app.core.db import get_engine

app = FastAPI(title="KotobaForge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(imports_router)
app.include_router(sources_router)
app.include_router(dashboard_router)


@app.get("/api/health")
def health(engine: Engine = Depends(get_engine)):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}

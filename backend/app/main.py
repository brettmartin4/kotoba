import mimetypes

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.imports import router as imports_router
from app.api.routes.items import router as items_router
from app.api.routes.lessons import router as lessons_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.sources import router as sources_router
from app.core.config import BACKEND_DIR
from app.core.db import get_engine

# Some Windows installs have a stray registry MIME mapping that makes Python's
# mimetypes module guess "text/plain" for .js -- browsers reject that content
# type for ES module scripts, which would blank-page the packaged frontend.
# Registering explicitly makes StaticFiles/FileResponse's guess correct
# regardless of the host OS's registry state.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

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
app.include_router(lessons_router)
app.include_router(reviews_router)
app.include_router(items_router)


@app.get("/api/health")
def health(engine: Engine = Depends(get_engine)):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}


# Serves the production frontend build (frontend/dist, from `npm run build`)
# when present, so start_kotobaforge.bat can run a single packaged process.
# Absent in plain dev mode (npm run dev on :5173 proxies to this API instead)
# and absent under pytest, so neither path is affected by this being missing.
_frontend_dist = BACKEND_DIR.parent / "frontend" / "dist"

if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # An unmatched /api/* path is a real 404, not a client-side route --
        # falling back to index.html here would silently mask API typos/bugs
        # behind a 200 HTML response instead of a clear error.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Root-level build outputs (e.g. favicon.svg) are served as themselves;
        # any client-side route (e.g. /browse, /items/5) falls back to
        # index.html so React Router can take over after a hard refresh.
        # resolve() + is_relative_to() rejects any "../" escape out of dist.
        candidate = (_frontend_dist / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_frontend_dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import check_connection

app = FastAPI(title="KotobaForge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "db": "ok" if check_connection() else "error"}

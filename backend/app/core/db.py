import sqlite3

from .config import settings


def get_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(settings.db_path)


def check_connection() -> bool:
    conn = get_connection()
    try:
        conn.execute("SELECT 1")
        return True
    finally:
        conn.close()

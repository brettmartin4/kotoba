from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Settings:
    db_path: Path = BACKEND_DIR / "data" / "kotobaforge.db"
    wordbank_folder: Path = BACKEND_DIR.parent / "wordbanks"
    daily_lesson_cap: int = 10
    lesson_batch_size: int = 5
    level_size: int = 20


settings = Settings()


def get_wordbank_folder() -> Path:
    return settings.wordbank_folder

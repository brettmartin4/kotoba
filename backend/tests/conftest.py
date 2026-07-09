import pytest

from app.core.db import create_sqlite_engine, init_db


@pytest.fixture
def engine(tmp_path):
    eng = create_sqlite_engine(tmp_path / "test.db")
    init_db(eng)
    return eng


@pytest.fixture
def wordbank_dir(tmp_path):
    d = tmp_path / "wordbanks"
    d.mkdir()
    return d

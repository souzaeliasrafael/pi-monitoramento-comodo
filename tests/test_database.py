from sqlalchemy import text

from app.config import Settings
from app.database.connection import create_database_engine, initialize_database


def test_file_database_and_idempotence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path.parent)
    engine = create_database_engine(Settings(database_url="sqlite:///nested/test.db"), base_dir=tmp_path)
    try:
        initialize_database(engine)
        assert (tmp_path / "nested/test.db").is_file()
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE probe (value INTEGER)"))
            connection.execute(text("INSERT INTO probe VALUES (42)"))
        initialize_database(engine)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT value FROM probe")).scalar_one() == 42
            assert connection.execute(text("PRAGMA integrity_check")).scalar_one() == "ok"
    finally:
        engine.dispose()


def test_memory_database():
    engine = create_database_engine(Settings(database_url="sqlite:///:memory:"))
    try:
        initialize_database(engine)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()


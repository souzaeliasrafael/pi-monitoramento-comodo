from datetime import datetime, timedelta

from sqlalchemy import inspect

from app.config import Settings
from app.data_sources.simulator import SimulatorDataSource
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository


def test_repository():
    engine = create_database_engine(Settings(database_url="sqlite:///:memory:"))
    initialize_database(engine)
    repo = Repository(engine)
    start = datetime(2026, 1, 1)
    source = SimulatorDataSource()
    rows = source.get_current_readings(start)
    assert repo.insert_readings(rows) == 4
    assert repo.insert_readings(rows) == 0
    assert repo.insert_readings(source.get_current_readings(start + timedelta(hours=1))) == 4
    assert len(repo.query()) == 8
    assert len(repo.query(start, start, "sensor_01")) == 1
    assert repo.latest("sensor_01")["timestamp"] == start + timedelta(hours=1)
    assert repo.latest("missing") is None
    assert all(row["count"] == 2 for row in repo.summary())
    indexes = inspect(engine).get_indexes("readings")
    assert {i["column_names"][0] for i in indexes} == {"timestamp", "device_id"}
    engine.dispose()

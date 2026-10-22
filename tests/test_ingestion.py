from datetime import datetime, timedelta
from dataclasses import replace

import pytest

from app.config import Settings
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.data_sources.simulator import SimulatorDataSource
from app.services.ingestion import generate_history, persist_batch, resume_simulator


def test_history_validation_and_resume():
    engine = create_database_engine(Settings(database_url="sqlite:///:memory:"))
    initialize_database(engine)
    repo = Repository(engine)
    start = datetime(2026, 1, 1)
    assert generate_history(repo, start, 2) == (2 * 96 + 1) * 4
    with pytest.raises(ValueError, match="sobreposto"):
        generate_history(repo, start, 1)
    last = repo.latest("energy_meter_01")
    source = SimulatorDataSource()
    resume_simulator(source, repo)
    rows = source.get_current_readings(last["timestamp"] + timedelta(minutes=15))
    assert rows[-1].energy_kwh == last["energy_kwh"]  # Madrugada sem iluminação.
    invalid = replace(rows[0], temperature_c=float("nan"))
    assert persist_batch(repo, [invalid, *rows[1:]]) == 3
    engine.dispose()

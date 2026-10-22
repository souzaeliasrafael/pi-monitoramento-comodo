from datetime import datetime, timedelta
from statistics import mean

import pytest

from app.data_sources.climate import temperature_reference
from app.data_sources.simulator import SimulatorDataSource


def test_maua_monthly_reference_and_continuity():
    assert temperature_reference(datetime(2026, 9, 15)) == (15, 23)
    assert temperature_reference(datetime(2026, 10, 15)) == (16, 24)
    boundary = datetime(2026, 10, 1)
    before = temperature_reference(boundary - timedelta(seconds=1))
    after = temperature_reference(boundary)
    assert max(abs(b - a) for a, b in zip(before, after)) < 0.001


def test_compact_history_covers_spring_without_energy_gaps():
    start, end = datetime(2026, 9, 1), datetime(2026, 10, 4, 12)
    batches = list(SimulatorDataSource().history_by_count(start, end, 5000))
    assert len(batches) * 4 == 5000
    assert batches[0][0].timestamp == start
    assert batches[-1][0].timestamp == end
    assert all(0 < (b[0].timestamp - a[0].timestamp).total_seconds() <= 3600 for a, b in zip(batches, batches[1:]))
    temperatures = [row.temperature_c for batch in batches for row in batch[:3]]
    assert 18 < mean(temperatures) < 23
    assert min(temperatures) >= 11
    assert max(temperatures) <= 33
    for batch in batches:
        for row in batch:
            row.validate()


@pytest.mark.parametrize("records", [4999, 0, 8])
def test_invalid_compact_history(records):
    with pytest.raises(ValueError):
        list(SimulatorDataSource().history_by_count(datetime(2026, 9, 1), datetime(2026, 10, 4), records))

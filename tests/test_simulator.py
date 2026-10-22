from datetime import datetime
from statistics import mean

import pytest

from app.data_sources.simulator import SimulatorDataSource


def test_temporal_simulation_and_reproducibility():
    start = datetime(2026, 1, 1)
    batches = list(SimulatorDataSource(42).history(start, 30))
    assert batches == list(SimulatorDataSource(42).history(start, 30))
    assert batches != list(SimulatorDataSource(43).history(start, 30))
    for batch in batches:
        assert len(batch) == 4
        for reading in batch:
            reading.validate()
    temps = [b[0].temperature_c for b in batches]
    assert max(temps) > 30
    assert max(abs(b - a) for a, b in zip(temps, temps[1:])) < 2
    assert 20 < mean(temps) < 29
    powers = [b[3].power_w for b in batches]
    assert {round(p / 15) for p in powers} == {0, 1, 2, 3, 4}
    assert 0 <= min(powers) < max(powers) <= 60
    voltages = [b[3].voltage_v for b in batches]
    assert max(voltages) - min(voltages) > 4
    for batch in batches:
        meter = batch[3]
        assert meter.current_a * meter.voltage_v == pytest.approx(meter.power_w)
    hourly = list(SimulatorDataSource(42).history(start, 30, interval_minutes=60))
    assert hourly[-1][3].energy_kwh == pytest.approx(batches[-1][3].energy_kwh)
    assert batches[0][3].energy_kwh == 0


def test_invalid_history():
    with pytest.raises(ValueError):
        list(SimulatorDataSource().history(datetime(2026, 1, 1), 0))

from datetime import datetime, timedelta
from dataclasses import replace

import pytest

from app.config import Settings
from app.data_sources.readings import Reading
from app.data_sources.simulator import SimulatorDataSource
from app.services.analytics import readings_frame, hourly_consumption
from app.services.alerts import active_alerts
from app.services.energy import energy_summary


@pytest.mark.parametrize("changes", [
    {"temperature_c": 100}, {"humidity_percent": 101}, {"humidity_percent": None},
    {"device_id": ""}, {"power_w": 100}, {"temperature_c": float("inf")},
])
def test_invalid_readings(changes):
    reading = Reading(datetime(2026, 1, 1), "sensor", 24, 55)
    with pytest.raises(ValueError):
        replace(reading, **changes).validate()


def test_counter_reset_and_long_gap_excluded():
    start = datetime(2026, 1, 1)
    frame = readings_frame([
        {"timestamp": start, "device_id": "meter", "energy_kwh": 10},
        {"timestamp": start + timedelta(minutes=30), "device_id": "meter", "energy_kwh": 11},
        {"timestamp": start + timedelta(hours=1), "device_id": "meter", "energy_kwh": 0},
        {"timestamp": start + timedelta(hours=4), "device_id": "meter", "energy_kwh": 5},
    ])
    hourly = hourly_consumption(frame)
    assert hourly.consumption_kwh.sum() == 1
    assert hourly.coverage_hours.sum() == 0.5
    assert hourly.attrs["excluded_intervals"] == 2


def test_stale_alerts_are_not_active():
    start = datetime(2026, 1, 1)
    frame = readings_frame([{"timestamp": start, "device_id": "sensor", "temperature_c": 38}])
    assert len(active_alerts(frame, Settings(), start)) == 1
    assert active_alerts(frame, Settings(), start + timedelta(days=1)) == []


def test_no_data_cost_estimate_is_unavailable():
    result = energy_summary(readings_frame([]), 0.95)
    assert result["estimated_month_cost"] is None
    assert result["today_coverage_hours"] == 0


def test_simulator_rejects_time_reversal():
    source = SimulatorDataSource()
    source.get_current_readings(datetime(2026, 1, 2))
    with pytest.raises(ValueError):
        source.get_current_readings(datetime(2026, 1, 1))

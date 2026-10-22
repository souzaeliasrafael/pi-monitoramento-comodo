from datetime import datetime, timedelta

import pytest

from app.services.analytics import readings_frame, environmental_summary, consumption_by_period, energy_statistics


def known_frame():
    start = datetime(2026, 1, 1, 23, 30)
    return readings_frame([
        {"timestamp": start + timedelta(minutes=30 * i), "device_id": "meter", "energy_kwh": i * 0.5, "power_w": 1000}
        for i in range(3)
    ] + [
        {"timestamp": start + timedelta(minutes=30 * i), "device_id": "sensor", "temperature_c": 20 + i * 2, "humidity_percent": 50}
        for i in range(3)
    ])


def test_known_statistics_and_midnight():
    frame = known_frame()
    stats = environmental_summary(frame)
    assert stats.loc["sensor", ("temperature_c", "mean")] == 22
    assert stats.loc["sensor", ("temperature_c", "median")] == 22
    assert stats.loc["sensor", ("temperature_c", "std")] == 2
    daily = consumption_by_period(frame)
    assert daily.consumption_kwh.tolist() == pytest.approx([0.5, 0.5])
    assert consumption_by_period(frame, "W-MON").consumption_kwh.sum() == 1
    assert consumption_by_period(frame, "MS").consumption_kwh.sum() == 1
    assert energy_statistics(frame)["mean_power_w"] == 1000


def test_empty_analysis():
    frame = readings_frame([])
    assert environmental_summary(frame).empty
    assert consumption_by_period(frame).empty
    assert energy_statistics(frame)["peak_hour"] is None

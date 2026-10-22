from datetime import datetime

import pytest

from app.services.analytics import readings_frame, consumption_by_period
from app.services.energy import energy_summary, with_cost
from app.data_sources.simulator import SimulatorDataSource
from dataclasses import asdict


def test_cost_and_estimate():
    frame = readings_frame([asdict(r) for batch in SimulatorDataSource().history(datetime(2026, 1, 1), 8) for r in batch])
    daily = consumption_by_period(frame)
    result = energy_summary(frame, 0.95, datetime(2026, 1, 9))
    assert result["total_kwh"] == pytest.approx(frame.energy_kwh.max())
    assert result["estimated_month_cost"] == pytest.approx(daily.tail(7).consumption_kwh.mean() * 31 * 0.95)
    assert result["today_kwh"] == 0
    assert with_cost(daily, 2).cost_brl.sum() == pytest.approx(result["total_kwh"] * 2)
    with pytest.raises(ValueError):
        with_cost(daily, -1)

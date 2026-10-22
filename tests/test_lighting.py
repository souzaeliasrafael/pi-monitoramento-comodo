from datetime import datetime, timedelta
from statistics import mean

import pytest

from app.config import Settings
from app.services.lighting import lighting_energy, lighting_power
from app.services.dynamic_usage import daily_sessions


def test_dynamic_occupancy_and_partial_loads():
    start = datetime(2026, 9, 1)
    hours, begins = [], []
    for i in range(33):
        day = start + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        sessions = daily_sessions(day)
        hours.append(sum((off-on).total_seconds()/3600 for on,off in sessions))
        begins.append(sessions[0][0].hour + sessions[0][0].minute/60)
        assert all(a[1] < b[0] for a,b in zip(sessions,sessions[1:]))
    assert 8 <= min(hours) <= mean(hours) <= max(hours) <= 10.000001
    assert len(set(begins)) > 20
    settings = Settings()
    powers = [lighting_power(start+timedelta(minutes=i),settings) for i in range(1440)]
    assert {round(p/15) for p in powers} == {0,1,2,3,4}
    # Independent minute sampling closely approximates exact integration.
    estimated = sum(powers) / 60000
    exact = lighting_energy(start,start+timedelta(days=1),settings)
    assert estimated == pytest.approx(exact,abs=.003)


def test_energy_is_additive_across_midnight_and_sampling_boundaries():
    settings=Settings()
    start=datetime(2026,10,1,19,17)
    middle=datetime(2026,10,2,8,23)
    end=datetime(2026,10,3,13,19)
    assert lighting_energy(start,end,settings) == pytest.approx(
        lighting_energy(start,middle,settings)+lighting_energy(middle,end,settings))
    assert lighting_power(datetime(2026,10,2,3),settings)==0


def test_saturdays_stop_at_noon_and_sundays_have_no_consumption():
    settings = Settings()
    for day in (datetime(2026,9,5), datetime(2026,9,12), datetime(2026,9,19), datetime(2026,9,26), datetime(2026,10,3)):
        noon = day + timedelta(hours=12)
        sunday = day + timedelta(days=1)
        monday = day + timedelta(days=2)
        sessions = daily_sessions(day)
        assert sessions
        assert all(on < off <= noon for on, off in sessions)
        assert 0 < lighting_energy(day, noon, settings) < .36
        assert lighting_energy(noon, sunday, settings) == 0
        assert lighting_energy(sunday, monday, settings) == 0
        assert not daily_sessions(sunday)
        assert all(lighting_power(noon + timedelta(minutes=i), settings) == 0 for i in range(36 * 60))

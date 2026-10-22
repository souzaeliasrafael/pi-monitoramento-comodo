from datetime import datetime, timedelta

from app.config import Settings
from app.database.connection import create_database_engine, initialize_database
from app.services.analytics import readings_frame
from app.services.alerts import detect_alerts, active_alerts, sync_alerts, load_alerts


def test_thresholds_cooldown_persistence_and_resolution():
    start = datetime(2026, 1, 1)
    frame = readings_frame([{"timestamp": start + timedelta(minutes=15*i), "device_id": "sensor",
                             "temperature_c": 36, "humidity_percent": 80} for i in range(28)])
    alerts = detect_alerts(frame, Settings())
    assert len(alerts) == 4
    assert all(a["level"] == "CRITICAL" for a in alerts)
    assert len(active_alerts(frame, Settings())) == 2
    engine = create_database_engine(Settings(database_url="sqlite:///:memory:"))
    initialize_database(engine)
    assert sync_alerts(engine, frame, Settings()) == 4
    assert sync_alerts(engine, frame, Settings()) == 0
    assert len(load_alerts(engine)) == 4
    frame.loc[frame.index[-1], ["temperature_c", "humidity_percent"]] = [24, 55]
    assert not active_alerts(frame, Settings())
    engine.dispose()


def test_normal_limits_and_power_peak():
    start = datetime(2026, 1, 1)
    normal = readings_frame([{"timestamp": start, "device_id": "sensor", "temperature_c": 30, "humidity_percent": 40}])
    assert not detect_alerts(normal, Settings())
    frame = readings_frame([{"timestamp": start + timedelta(minutes=15*i), "device_id": "meter", "power_w": 500 if i < 30 else 3000}
                            for i in range(31)])
    assert detect_alerts(frame, Settings())[-1]["type"] == "CONSUMO_ELEVADO"

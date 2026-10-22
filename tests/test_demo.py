from datetime import datetime
from pathlib import Path
import sqlite3

from app.config import Settings
from app.services.demo import setup_demo
from app.database.connection import create_database_engine
from app.services.equipment import add_equipment, list_equipment


def test_demo_from_zero_and_backup(tmp_path):
    path = tmp_path / "demo.db"
    settings = Settings(database_url="sqlite:///" + path.as_posix())
    kwargs = {"now": datetime(2026, 2, 1, 12), "model_dir": tmp_path / "models", "report_dir": tmp_path / "reports"}
    first = setup_demo(settings, 30, **kwargs)
    assert first["readings"] > 30 * 96 * 4
    assert first["alerts"] > 0
    assert first["forecast_kwh"] > 0
    assert first["energy"]["today_kwh"] == 0  # Domingo sem uso do circuito.
    assert Path(first["report"]).is_file()
    engine = create_database_engine(settings)
    add_equipment(engine, "Luminária futura", 1, 15, active_from=datetime(2026, 2, 2))
    second = setup_demo(settings, 30, **kwargs)
    assert len(list_equipment(engine)) == 1
    engine.dispose()
    assert first["forecast_kwh"] == second["forecast_kwh"]
    assert Path(second["backup"]).is_file()
    with sqlite3.connect(second["backup"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == first["readings"]


def test_compact_demo_retrains_and_preserves_daily_coverage(tmp_path):
    path = tmp_path / "compact.db"
    result = setup_demo(Settings(database_url="sqlite:///" + path.as_posix()), 33,
                        records=5000, now=datetime(2026, 10, 4, 12),
                        model_dir=tmp_path / "models", report_dir=tmp_path / "reports")
    assert result["readings"] == 5000
    assert result["energy"]["excluded_intervals"] == 0
    assert result["forecast_kwh"] > 0
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 5000
        assert all(count == 1250 for _, count in conn.execute("SELECT device_id, COUNT(*) FROM readings GROUP BY device_id"))

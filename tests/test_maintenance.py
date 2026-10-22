from datetime import datetime

from app.config import Settings
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.ingestion import generate_history
from app.services.maintenance import maintain_alerts, scheduled_weekly_report
from app.logging_config import command_entrypoint


def test_weekly_report_once(tmp_path):
    settings = Settings(database_url="sqlite:///:memory:")
    engine = create_database_engine(settings)
    initialize_database(engine)
    now = datetime(2026, 2, 2, 12)  # Segunda-feira
    assert scheduled_weekly_report(engine, settings, now=now, report_dir=tmp_path) is None
    generate_history(Repository(engine), datetime(2026, 1, 19), 14)
    maintain_alerts(engine, settings, now=now)
    report = scheduled_weekly_report(engine, settings, now=now, report_dir=tmp_path)
    assert report.is_file()
    before = report.stat().st_mtime_ns
    assert scheduled_weekly_report(engine, settings, now=now, report_dir=tmp_path) == report
    assert report.stat().st_mtime_ns == before
    engine.dispose()


def test_cli_failure_does_not_log_secret(caplog):
    @command_entrypoint
    def fails():
        raise RuntimeError("private-token-never-log")
    assert fails() == 1
    assert "private-token-never-log" not in caplog.text

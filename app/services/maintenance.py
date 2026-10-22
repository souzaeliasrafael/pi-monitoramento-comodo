"""Alertas e relatório semanal local mantidos pelo processo coletor."""

from datetime import timedelta
from pathlib import Path
import logging

from app.config import PROJECT_ROOT, local_now
from app.database.repository import Repository
from app.services.analytics import readings_frame
from app.services.alerts import sync_alerts, load_alerts
from app.services.reports import generate_weekly_report
from app.ml.predict import predict_consumption

logger = logging.getLogger(__name__)


def maintain_alerts(engine, settings, now=None):
    now = now or local_now()
    frame = readings_frame(Repository(engine).query(start=now - timedelta(days=2), end=now))
    return sync_alerts(engine, frame, settings)


def scheduled_weekly_report(engine, settings, *, now=None, report_dir: Path = PROJECT_ROOT / "reports"):
    """Uma vez por semana: última semana de segunda a domingo, após o fechamento."""
    now = now or local_now()
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    # Diferencia bancos configurados no mesmo diretório de artefatos.
    import hashlib
    database_key = hashlib.sha256(str(engine.url).encode()).hexdigest()[:10]
    output = Path(report_dir) / f"automatico_{database_key}_{end:%Y%m%d}.html"
    if output.exists():
        return output
    frame = readings_frame(Repository(engine).query())
    if frame.empty or frame.timestamp.min() > end - timedelta(days=7) or frame.timestamp.max() < end:
        return None
    forecast = None
    try:
        forecast, _ = predict_consumption(frame, settings.energy_price_kwh)
    except ValueError:
        logger.info("Relatório automático será gerado sem previsão disponível.")
    report = generate_weekly_report(frame, load_alerts(engine), settings, end=end,
                                    forecast=forecast, output_dir=Path(report_dir))
    report.replace(output)
    logger.info("Relatório semanal automático concluído.")
    return output

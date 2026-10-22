"""Preparação reprodutível da apresentação acadêmica."""

from datetime import timedelta
from pathlib import Path
import json
import logging
import sqlite3

from app.config import Settings, PROJECT_ROOT, local_now
from app.data_sources.simulator import SimulatorDataSource
from app.database.connection import create_database_engine, initialize_database
from app.database.models import Base
from app.database.repository import Repository
from app.services.ingestion import generate_history, resume_simulator, persist_batch
from app.services.analytics import readings_frame
from app.services.energy import energy_summary
from app.services.alerts import sync_alerts, load_alerts
from app.services.equipment import list_equipment
from app.services.reports import generate_weekly_report
from app.ml.train import train_models
from app.ml.predict import predict_consumption
from app.ml.learning import replay_learning, adaptive_forecast

logger = logging.getLogger(__name__)


def setup_demo(settings: Settings, days=60, *, now=None, records: int | None = None,
               model_dir: Path = PROJECT_ROOT / "models", report_dir: Path = PROJECT_ROOT / "reports") -> dict:
    """Recria tabelas do sistema, fazendo backup SQLite antes de qualquer alteração."""
    if not 30 <= days <= 90:
        raise ValueError("A demonstração exige entre 30 e 90 dias.")
    if settings.data_source != "simulator":
        raise ValueError("A demonstração exige DATA_SOURCE=simulator.")
    now = now or local_now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days)
    # Valida o tamanho antes de fazer backup ou alterar qualquer tabela.
    if records is not None:
        if not isinstance(records, int) or records < 8 or records % 4:
            raise ValueError("Registros devem ser um múltiplo de quatro, com mínimo de oito.")
        if (now - start) / (records // 4 - 1) > timedelta(hours=1):
            raise ValueError("Quantidade insuficiente de registros para cobrir o período sem lacunas.")
    engine = create_database_engine(settings)
    backup = None
    try:
        database = engine.url.database
        if database != ":memory:" and Path(database).is_file() and Path(database).stat().st_size:
            backup_dir = Path(database).parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / f"{Path(database).stem}_{local_now():%Y%m%d_%H%M%S%f}.db"
            with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
                source.backup(target)
            logger.info("Backup do banco anterior criado: %s", backup.name)
        # Cadastros são configuração do usuário e sobrevivem à recriação das leituras.
        Base.metadata.drop_all(engine, tables=[table for table in Base.metadata.sorted_tables if table.name != "equipment"])
        initialize_database(engine)
        repository = Repository(engine)
        equipment_provider = lambda: list_equipment(engine)
        if records is not None:
            source = SimulatorDataSource(settings.simulation_seed, settings=settings, equipment_provider=equipment_provider)
            pending = []
            for batch in source.history_by_count(start, now, records):
                pending.extend(batch)
                if len(pending) >= 2000:
                    persist_batch(repository, pending)
                    pending = []
            persist_batch(repository, pending)
        else:
            generate_history(repository, start, days, settings.simulation_seed, settings=settings, equipment_provider=equipment_provider)
            source = SimulatorDataSource(settings.simulation_seed, settings=settings, equipment_provider=equipment_provider)
            resume_simulator(source, repository)
            t = today
            pending = []
            while t < now:
                t = min(t + timedelta(minutes=15), now)
                pending.extend(source.get_current_readings(t))
            persist_batch(repository, pending)
        frame = readings_frame(repository.query())
        sync_alerts(engine, frame, settings)
        model_dir, report_dir = Path(model_dir), Path(report_dir)
        model_path = model_dir / "energy_model.joblib"
        metadata = train_models(frame, settings.simulation_seed, model_path)
        forecast, _ = predict_consumption(frame, settings.energy_price_kwh, model_path=model_path)
        replay_learning(engine, frame, settings.simulation_seed)
        adaptive, _ = adaptive_forecast(engine, settings.energy_price_kwh)
        if adaptive is not None:
            forecast = adaptive
        forecast.to_csv(model_dir / "forecast.csv", index=False)
        report = generate_weekly_report(frame, load_alerts(engine), settings, end=today, forecast=forecast, output_dir=report_dir)
        summary = {"readings": len(frame), "days": days, "alerts": len(load_alerts(engine)),
                   "model": metadata["selected_model"], "forecast_kwh": float(forecast.prediction_kwh.sum()),
                   "forecast_cost_brl": float(forecast.cost_brl.sum()), "test_metrics": metadata["test"][metadata["selected_model"]],
                   "energy": energy_summary(frame, settings.energy_price_kwh, now),
                   "report": str(report), "backup": str(backup) if backup else None,
                   "simulated_data_only": True}
        (report_dir / "demo_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        logger.info("Demonstração pronta: %d leituras, %d alertas.", summary["readings"], summary["alerts"])
        return summary
    finally:
        engine.dispose()

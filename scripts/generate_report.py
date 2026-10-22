import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from datetime import datetime
import logging

from app.config import load_settings
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.analytics import readings_frame
from app.services.alerts import sync_alerts, load_alerts
from app.services.reports import generate_weekly_report
from app.ml.predict import predict_consumption
from app.logging_config import command_entrypoint


@command_entrypoint
def main():
    parser = argparse.ArgumentParser(description="Relatório dos 7 dias anteriores à data final.")
    parser.add_argument("--end", type=datetime.fromisoformat)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    engine = create_database_engine(settings)
    try:
        initialize_database(engine)
        frame = readings_frame(Repository(engine).query())
        sync_alerts(engine, frame, settings)
        forecast = None
        try:
            forecast, _ = predict_consumption(frame, settings.energy_price_kwh)
        except ValueError:
            logging.info("Relatório sem previsão: modelo indisponível ou histórico incompatível.")
        print(generate_weekly_report(frame, load_alerts(engine), settings, end=args.end, forecast=forecast))
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

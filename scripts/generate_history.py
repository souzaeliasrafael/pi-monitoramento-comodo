"""Gera histórico simulado. Execute da raiz, via -m ou caminho do script."""
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from datetime import datetime, timedelta
import logging

from app.config import load_settings, local_now
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.ingestion import generate_history
from app.logging_config import command_entrypoint
from app.services.analytics import readings_frame
from app.services.alerts import sync_alerts


@command_entrypoint
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--interval-minutes", type=int, default=15)
    parser.add_argument("--start", type=datetime.fromisoformat)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    settings = load_settings()
    engine = create_database_engine(settings)
    try:
        initialize_database(engine)
        start = args.start or local_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=args.days)
        generate_history(Repository(engine), start, args.days, settings.simulation_seed, args.interval_minutes, settings)
        sync_alerts(engine, readings_frame(Repository(engine).query()), settings)
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

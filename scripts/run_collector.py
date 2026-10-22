"""Coletor local; Ctrl+C encerra. --once executa apenas uma coleta."""
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import logging
import time

from app.config import load_settings, local_now
from app.ml.learning import learning_step
from app.services.analytics import readings_frame
from app.data_sources.factory import create_source
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.ingestion import collect_once, resume_simulator
from app.services.maintenance import maintain_alerts, scheduled_weekly_report
from app.logging_config import command_entrypoint

logger = logging.getLogger(__name__)


@command_entrypoint
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    settings = load_settings()
    engine = create_database_engine(settings)
    try:
        initialize_database(engine)
        repository = Repository(engine)
        source = create_source(settings, engine=engine)
        resume_simulator(source, repository)
        logger.info("Coletor iniciado; fonte: %s", settings.data_source)
        while True:
            try:
                count = collect_once(source, repository)
                logger.info("Coleta concluída: %d registros inseridos.", count)
                maintain_alerts(engine, settings)
                learning_step(engine, readings_frame(repository.query()), issued_at=local_now(), seed=settings.simulation_seed)
                scheduled_weekly_report(engine, settings)
            except NotImplementedError:
                logger.error("Tuya ainda não implementada; use DATA_SOURCE=simulator.")
                return 1
            except Exception:
                logger.error("Falha na coleta; verifique fonte, configuração e banco.")
                if args.once:
                    return 1
            if args.once:
                return 0
            time.sleep(settings.simulation_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Coletor encerrado pelo usuário.")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

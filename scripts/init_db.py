"""Execute com python -m scripts.init_db."""

import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import create_database_engine, initialize_database
from app.logging_config import command_entrypoint

logger = logging.getLogger(__name__)


@command_entrypoint
def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    engine = None
    try:
        engine = create_database_engine()
        initialize_database(engine)
        logger.info("Banco SQLite inicializado com as tabelas do sistema.")
        return 0
    except (ValueError, OSError, SQLAlchemyError):
        logger.error("Falha ao inicializar o banco. Verifique a configuração e as permissões da pasta.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())


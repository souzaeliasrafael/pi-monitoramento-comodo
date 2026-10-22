import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
from app.config import load_settings
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.analytics import readings_frame
from app.ml.train import train_models
from app.logging_config import command_entrypoint


@command_entrypoint
def main():
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    engine = create_database_engine(settings)
    try:
        initialize_database(engine)
        metadata = train_models(readings_frame(Repository(engine).query()), settings.simulation_seed)
        print("Modelo selecionado:", metadata["selected_model"])
        print("Métricas de teste:", metadata["test"][metadata["selected_model"]])
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

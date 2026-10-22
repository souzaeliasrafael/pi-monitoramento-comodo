import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from app.config import PROJECT_ROOT
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.analytics import readings_frame
from app.ml.features import daily_dataset, training_dataset, temporal_split
from app.ml.evaluate import Baseline, evaluate_blocks
from app.logging_config import command_entrypoint


@command_entrypoint
def main():
    engine = create_database_engine()
    try:
        initialize_database(engine)
        daily = daily_dataset(readings_frame(Repository(engine).query()))
        _, validation, test = temporal_split(training_dataset(daily))
        results = {name: {"validation": evaluate_blocks(Baseline(name), daily, validation.index)[0],
                          "test": evaluate_blocks(Baseline(name), daily, test.index)[0]}
                   for name in ("previous", "moving_average")}
        path = PROJECT_ROOT / "models/baselines.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2, allow_nan=False), encoding="utf-8")
        print(path)
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

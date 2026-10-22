from dataclasses import asdict
from datetime import datetime

import joblib
import pytest

from app.data_sources.simulator import SimulatorDataSource
from app.services.analytics import readings_frame
from app.ml.train import train_models


def test_training_selection_and_saved_artifact(tmp_path):
    frame = readings_frame([asdict(r) for batch in SimulatorDataSource().history(datetime(2026, 1, 1), 40) for r in batch])
    path = tmp_path / "model.joblib"
    metadata = train_models(frame, model_path=path)
    expected = min(metadata["validation"], key=lambda n: (metadata["validation"][n]["mae"], metadata["validation"][n]["rmse"]))
    assert metadata["selected_model"] == expected
    assert len(metadata["validation"]) == len(metadata["test"]) == 5
    assert metadata["split"]["train"]["end"] < metadata["split"]["validation"]["start"]
    assert metadata["split"]["validation"]["end"] < metadata["split"]["test"]["start"]
    assert joblib.load(path)["metadata"] == metadata
    assert path.with_suffix(".json").is_file()
    with pytest.raises(ValueError, match="insuficiente"):
        train_models(frame.head(4), model_path=tmp_path / "small.joblib")

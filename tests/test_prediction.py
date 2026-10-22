from dataclasses import asdict
from datetime import datetime

import pytest
import pandas as pd

from app.data_sources.simulator import SimulatorDataSource
from app.services.analytics import readings_frame
from app.ml.train import train_models
from app.ml.predict import predict_consumption, load_model


def test_forecast_roundtrip_cost_and_history_guard(tmp_path):
    frame = readings_frame([asdict(r) for b in SimulatorDataSource().history(datetime(2026, 1, 1), 30) for r in b])
    path = tmp_path / "energy.joblib"
    train_models(frame, model_path=path)
    forecast, metadata = predict_consumption(frame, 0.95, model_path=path)
    assert len(forecast) == 7
    assert forecast.timestamp.min() == pd.Timestamp("2026-01-31")
    assert forecast.cost_brl.sum() == pytest.approx(forecast.prediction_kwh.sum() * 0.95)
    assert (forecast.lower_kwh <= forecast.prediction_kwh).all()
    assert (forecast.upper_kwh >= forecast.prediction_kwh).all()
    assert metadata["simulated_data_only"]
    changed = frame.copy()
    changed["energy_kwh"] *= 2
    with pytest.raises(ValueError, match="outro histórico"):
        predict_consumption(changed, 0.95, model_path=path)


def test_missing_and_corrupt_model(tmp_path):
    with pytest.raises(ValueError, match="inexistente"):
        load_model(tmp_path / "absent.joblib")
    path = tmp_path / "broken.joblib"
    path.write_text("not a model", encoding="utf-8")
    with pytest.raises(ValueError, match="inválido"):
        load_model(path)

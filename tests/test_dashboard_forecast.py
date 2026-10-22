from dataclasses import asdict
from datetime import datetime

from streamlit.testing.v1 import AppTest

from app.data_sources.simulator import SimulatorDataSource
from app.services.analytics import readings_frame
from app.ml.train import train_models


def forecast_app(frame, path):
    from app.config import Settings
    from app.dashboard.forecast import render_forecast
    render_forecast(frame, Settings(), model_path=path)


def test_dashboard_forecast_with_model(tmp_path):
    frame = readings_frame([asdict(r) for b in SimulatorDataSource().history(datetime(2026, 1, 1), 30) for r in b])
    path = tmp_path / "model.joblib"
    train_models(frame, model_path=path)
    app = AppTest.from_function(forecast_app, args=(frame, path), default_timeout=30).run()
    assert not app.exception
    assert len(app.metric) == 4
    assert "kWh" in app.metric[0].value
    assert len(app.table[0].value) == 5

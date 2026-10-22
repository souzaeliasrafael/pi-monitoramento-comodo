from dataclasses import asdict
from datetime import datetime

import pandas as pd
import pytest

from app.config import Settings
from app.data_sources.simulator import SimulatorDataSource
from app.database.connection import create_database_engine, initialize_database
from app.ml.learning import learning_step, forecast_records, adaptive_forecast
from app.ml.features import daily_dataset
from app.services.analytics import readings_frame


def test_arrivals_score_preserved_forecasts_and_retrain_without_future_leak(tmp_path):
    settings = Settings()
    frame = readings_frame([asdict(r) for batch in SimulatorDataSource(settings=settings).history(
        datetime(2026, 9, 1), 30, interval_minutes=60) for r in batch])
    engine = create_database_engine(Settings(database_url="sqlite:///" + (tmp_path / "learning.db").as_posix()))
    initialize_database(engine)
    # The full frame contains future observations, but only arrivals <= cutoff may be used.
    issue = pd.Timestamp("2026-09-23")
    assert learning_step(engine, frame, issued_at=issue) == 7
    first = forecast_records(engine)
    assert (first.target > first.issued_at).all()
    assert (first.training_end < first.issued_at).all()
    assert first.actual.isna().all()
    assert learning_step(engine, frame, issued_at=issue + pd.Timedelta(hours=12)) == 0
    other = create_database_engine(Settings(database_url="sqlite:///" + (tmp_path / "truncated.db").as_posix()))
    initialize_database(other)
    learning_step(other, frame[frame.timestamp <= issue], issued_at=issue)
    pd.testing.assert_series_equal(first.prediction, forecast_records(other).prediction)
    for arrival in pd.date_range("2026-09-24", "2026-09-29"):
        assert learning_step(engine, frame, issued_at=arrival) == 7
    records = forecast_records(engine)
    original = records[records.issued_at == issue]
    assert original.prediction.tolist() == first.prediction.tolist()
    actuals = daily_dataset(frame).consumption_kwh
    scored = records.dropna(subset=["actual"])
    assert (scored.evaluated_at > scored.target).all()
    for row in scored.itertuples():
        assert row.actual == pytest.approx(actuals.loc[row.target])
    forecast, _ = adaptive_forecast(engine, settings.energy_price_kwh)
    assert len(forecast) == 7
    assert forecast.lower_kwh.notna().all()
    assert forecast.prediction_kwh.mean() != pytest.approx(first.prediction.mean())
    assert abs(scored.actual - scored.prediction).max() > .01
    engine.dispose()
    other.dispose()

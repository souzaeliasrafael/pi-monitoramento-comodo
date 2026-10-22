from dataclasses import asdict
from datetime import datetime

import numpy as np

from app.data_sources.simulator import SimulatorDataSource
from app.services.analytics import readings_frame
from app.ml.features import daily_dataset, make_features, training_dataset, temporal_split, FEATURES


def test_features_do_not_use_target_day_or_future():
    frame = readings_frame([asdict(r) for b in SimulatorDataSource().history(datetime(2026, 1, 1), 40) for r in b])
    daily = daily_dataset(frame)
    assert len(daily) == 40
    before = make_features(daily)
    changed = daily.copy()
    changed.iloc[20:] = changed.iloc[20:] * 10
    after = make_features(changed)
    np.testing.assert_allclose(before.iloc[20][FEATURES], after.iloc[20][FEATURES])
    assert before.iloc[20].lag_1 == daily.iloc[19].consumption_kwh
    dataset = training_dataset(daily)
    assert not dataset.isna().any().any()
    train, validation, test = temporal_split(dataset)
    assert train.index.max() < validation.index.min() < test.index.min()


def test_missing_day_is_not_bridged():
    frame = readings_frame([asdict(r) for b in SimulatorDataSource().history(datetime(2026, 1, 1), 20) for r in b])
    frame = frame[frame.timestamp.dt.day != 10]
    daily = daily_dataset(frame)
    assert np.isnan(daily.loc["2026-01-10", "consumption_kwh"])
    features = training_dataset(daily)
    assert "2026-01-11" not in features.index

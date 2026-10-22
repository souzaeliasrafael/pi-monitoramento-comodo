import numpy as np
import pandas as pd
import pytest

from app.ml.evaluate import Baseline, metrics, recursive_forecast, evaluate_blocks


def constant_daily(days=30):
    return pd.DataFrame({"consumption_kwh": [12.] * days, "temperature_c": [24.] * days,
                         "humidity_percent": [55.] * days, "power_w": [500.] * days},
                        index=pd.date_range("2026-01-01", periods=days, name="timestamp"))


def test_metrics_and_zero_mape():
    result = metrics([0, 2], [1, 4])
    assert result["mae"] == 1.5
    assert result["rmse"] == pytest.approx(np.sqrt(2.5))
    assert result["mape_percent"] == 100
    assert metrics([0], [0])["mape_percent"] is None


def test_baseline_recursive_and_no_future_covariates():
    daily = constant_daily()
    for kind in ("previous", "moving_average"):
        baseline = Baseline(kind)
        result = recursive_forecast(baseline, daily.iloc[:20])
        assert result.prediction_kwh.tolist() == [12.] * 7
        scores, _ = evaluate_blocks(baseline, daily, daily.index[-7:])
        assert scores["mae"] == 0
    class CovariateModel:
        def predict(self, x):
            return x.temperature_lag_1.to_numpy()
    expected = recursive_forecast(CovariateModel(), daily.iloc[:20])
    daily.iloc[20:, daily.columns.get_loc("temperature_c")] = 99
    observed = recursive_forecast(CovariateModel(), daily.iloc[:20])
    pd.testing.assert_frame_equal(expected, observed)

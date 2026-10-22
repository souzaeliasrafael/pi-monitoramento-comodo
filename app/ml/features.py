"""Previsão diária: covariáveis ambientais somente defasadas, nunca futuras."""

import numpy as np
import pandas as pd

from app.services.analytics import consumption_by_period

FEATURES = ["day_of_week", "weekend", "week_sin", "week_cos", "lag_1", "lag_2", "lag_7",
            "rolling_7", "temperature_lag_1", "humidity_lag_1", "power_lag_1"]


def daily_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    daily = consumption_by_period(frame)
    if daily.empty:
        raise ValueError("Histórico insuficiente: não há intervalos de energia válidos.")
    daily = daily.set_index("timestamp").asfreq("D")
    environment = frame.set_index("timestamp")[["temperature_c", "humidity_percent", "power_w"]].resample("D").mean()
    daily = daily.join(environment)
    # Dias parciais e lacunas continuam ausentes, não viram consumo zero.
    daily.loc[daily.coverage_hours < 23.999, "consumption_kwh"] = np.nan
    return daily


def make_features(daily: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(index=daily.index)
    weekday = daily.index.dayofweek
    result["day_of_week"] = weekday
    result["weekend"] = (weekday >= 5).astype(int)
    result["week_sin"] = np.sin(weekday * 2 * np.pi / 7)
    result["week_cos"] = np.cos(weekday * 2 * np.pi / 7)
    for lag in (1, 2, 7):
        result[f"lag_{lag}"] = daily.consumption_kwh.shift(lag)
    result["rolling_7"] = daily.consumption_kwh.shift(1).rolling(7, min_periods=7).mean()
    for original, feature in [("temperature_c", "temperature_lag_1"),
                              ("humidity_percent", "humidity_lag_1"), ("power_w", "power_lag_1")]:
        result[feature] = daily[original].shift(1)
    result["target_kwh"] = daily.consumption_kwh
    return result.replace([np.inf, -np.inf], np.nan)


def training_dataset(daily: pd.DataFrame) -> pd.DataFrame:
    return make_features(daily).dropna(subset=[*FEATURES, "target_kwh"])


def temporal_split(dataset: pd.DataFrame):
    if len(dataset) < 21:
        raise ValueError("Histórico insuficiente: gere pelo menos 30 dias completos (60 recomendados).")
    if not dataset.index.is_monotonic_increasing or dataset.index.has_duplicates:
        raise ValueError("Dataset deve estar em ordem temporal, sem duplicatas.")
    first, second = int(len(dataset) * 0.6), int(len(dataset) * 0.8)
    return dataset.iloc[:first].copy(), dataset.iloc[first:second].copy(), dataset.iloc[second:].copy()

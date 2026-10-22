"""Métricas e avaliação temporal em blocos de até sete dias recursivos."""

import numpy as np
import pandas as pd

from app.ml.features import FEATURES, make_features


class Baseline:
    def __init__(self, strategy: str):
        if strategy not in {"previous", "moving_average"}:
            raise ValueError("Baseline desconhecido.")
        self.strategy = strategy

    def predict(self, features):
        return features["lag_1" if self.strategy == "previous" else "rolling_7"].to_numpy()

    def get_params(self, deep=True):
        return {"strategy": self.strategy}


def metrics(actual, predicted) -> dict:
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape or actual.size == 0 or not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Métricas exigem vetores finitos, não vazios e de mesmo tamanho.")
    errors = actual - predicted
    mask = np.abs(actual) > 1e-8
    return {"mae": float(np.mean(np.abs(errors))), "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "mape_percent": float(np.mean(np.abs(errors[mask] / actual[mask])) * 100) if mask.any() else None,
            "mape_count": int(mask.sum()), "samples": int(actual.size)}


def recursive_forecast(model, history: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    """Covariáveis futuras usam persistência semanal; consumo é realimentado por previsão."""
    if not 1 <= days <= 31:
        raise ValueError("Horizonte deve estar entre 1 e 31 dias.")
    history = history.copy()
    required = ["consumption_kwh", "temperature_c", "humidity_percent", "power_w"]
    if len(history) < 7 or history[required].tail(7).isna().any().any():
        raise ValueError("Previsão exige sete dias recentes completos e consecutivos.")
    if not history.index.equals(pd.date_range(history.index.min(), history.index.max(), freq="D", name=history.index.name)):
        raise ValueError("Histórico deve ter frequência diária regular.")
    rows = []
    for _ in range(days):
        date = history.index[-1] + pd.Timedelta(days=1)
        previous_week = history.iloc[-7]
        history.loc[date] = np.nan
        x = make_features(history).loc[[date], FEATURES]
        if x.isna().any().any():
            raise ValueError("Histórico insuficiente para montar as features de previsão.")
        value = float(model.predict(x)[0])
        if not np.isfinite(value):
            raise ValueError("Modelo produziu previsão não finita.")
        value = max(0, value)
        history.loc[date, ["consumption_kwh", "temperature_c", "humidity_percent", "power_w"]] = [
            value, previous_week.temperature_c, previous_week.humidity_percent, value * 1000 / 24]
        rows.append({"timestamp": date, "prediction_kwh": value})
    return pd.DataFrame(rows)


def evaluate_blocks(model, daily: pd.DataFrame, dates: pd.DatetimeIndex):
    """Cada origem usa somente dias anteriores; observações do bloco não realimentam a previsão."""
    predicted, actual = [], []
    if dates.empty:
        raise ValueError("Período de avaliação vazio.")
    for offset in range(0, len(dates), 7):
        block = dates[offset:offset + 7]
        if not block.equals(pd.date_range(block[0], periods=len(block), name=block.name)):
            raise ValueError("Avaliação exige blocos de dias consecutivos sem lacunas.")
        forecast = recursive_forecast(model, daily[daily.index < block[0]], len(block))
        predicted.extend(forecast.prediction_kwh)
        actual.extend(daily.loc[block, "consumption_kwh"])
    return metrics(actual, predicted), np.asarray(actual) - np.asarray(predicted)

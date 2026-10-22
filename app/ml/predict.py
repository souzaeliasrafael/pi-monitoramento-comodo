"""Previsão experimental de sete dias, usando somente artefatos locais confiáveis."""

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.evaluate import recursive_forecast
from app.ml.features import daily_dataset, FEATURES
from app.ml.train import MODEL_PATH, data_signature

logger = logging.getLogger(__name__)


def load_model(model_path: Path = MODEL_PATH):
    path = Path(model_path)
    if not path.is_file():
        raise ValueError("Modelo inexistente. Execute python scripts/train_model.py.")
    try:
        bundle = joblib.load(path)
        metadata = bundle["metadata"]
        if metadata["schema_version"] != 1 or metadata["features"] != FEATURES:
            raise ValueError("Versão incompatível.")
        if not hasattr(bundle["model"], "predict"):
            raise ValueError("Modelo inválido.")
        return bundle
    except Exception:
        raise ValueError("Modelo inválido ou incompatível. Treine novamente neste ambiente.") from None


def predict_consumption(frame, price: float, *, days: int = 7, model_path: Path = MODEL_PATH):
    if not np.isfinite(price) or price < 0:
        raise ValueError("Tarifa inválida.")
    bundle = load_model(model_path)
    metadata = bundle["metadata"]
    daily = daily_dataset(frame)
    last_complete = daily.consumption_kwh.last_valid_index()
    if last_complete is None:
        raise ValueError("Histórico insuficiente: não há dias completos.")
    history = daily.loc[:last_complete]
    training_start = pd.Timestamp(metadata["history_start"])
    training_end = pd.Timestamp(metadata["history_end"])
    if history.index.max() < training_end or data_signature(history.loc[training_start:training_end]) != metadata["data_signature"]:
        raise ValueError("O modelo pertence a outro histórico ou os dados foram alterados. Treine novamente.")
    forecast = recursive_forecast(bundle["model"], history, days)
    # Faixa descritiva dos erros observados; não declarar cobertura probabilística.
    spread = metadata["uncertainty_abs_q90"]
    forecast["lower_kwh"] = (forecast.prediction_kwh - spread).clip(lower=0)
    forecast["upper_kwh"] = forecast.prediction_kwh + spread
    forecast["cost_brl"] = forecast.prediction_kwh * price
    logger.info("Previsão experimental gerada: %d dias, %.2f kWh.", days, forecast.prediction_kwh.sum())
    return forecast, metadata

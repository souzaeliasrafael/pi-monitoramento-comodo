"""Seleção temporal incluindo baselines; teste isolado da seleção."""

import hashlib
import json
import logging
from pathlib import Path
import os
import tempfile

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

from app.config import PROJECT_ROOT, local_now
from app.ml.features import daily_dataset, training_dataset, temporal_split, FEATURES
from app.ml.evaluate import Baseline, evaluate_blocks

logger = logging.getLogger(__name__)
MODEL_PATH = PROJECT_ROOT / "models/energy_model.joblib"
SIGNATURE_COLUMNS = ["consumption_kwh", "temperature_c", "humidity_percent", "power_w"]


def data_signature(daily):
    data = daily[SIGNATURE_COLUMNS].round(8).to_csv(date_format="%Y-%m-%d", float_format="%.8f")
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def candidates(seed=42):
    return {"Anterior": Baseline("previous"), "Média móvel 7 dias": Baseline("moving_average"),
            "LinearRegression": LinearRegression(),
            "RandomForestRegressor": RandomForestRegressor(n_estimators=100, max_depth=5, min_samples_leaf=2, random_state=seed, n_jobs=1),
            "GradientBoostingRegressor": GradientBoostingRegressor(n_estimators=80, max_depth=2, learning_rate=0.05, random_state=seed)}


def fit_model(model, dataset):
    if not isinstance(model, Baseline):
        model.fit(dataset[FEATURES], dataset.target_kwh)
    return model


def train_models(frame, seed=42, model_path: Path = MODEL_PATH) -> dict:
    daily = daily_dataset(frame)
    dataset = training_dataset(daily)
    train, validation, test = temporal_split(dataset)
    validation_scores, errors = {}, {}
    for name, model in candidates(seed).items():
        fit_model(model, train)
        validation_scores[name], errors[name] = evaluate_blocks(model, daily, validation.index)
    winner = min(validation_scores, key=lambda n: (validation_scores[n]["mae"], validation_scores[n]["rmse"]))
    train_validation = dataset.loc[dataset.index < test.index.min()]
    test_scores = {}
    for name, model in candidates(seed).items():
        fit_model(model, train_validation)
        test_scores[name], _ = evaluate_blocks(model, daily, test.index)
    final_model = fit_model(candidates(seed)[winner], dataset)
    last_day = dataset.index.max()
    signature_data = daily.loc[:last_day]
    metadata = {
        "schema_version": 1, "selected_model": winner, "trained_at": local_now().isoformat(),
        "simulated_data_only": True, "seed": seed, "features": FEATURES,
        "sklearn_version": sklearn.__version__, "parameters": final_model.get_params(),
        "validation": validation_scores, "test": test_scores,
        "split": {name: {"start": str(part.index.min().date()), "end": str(part.index.max().date()), "days": len(part)}
                  for name, part in [("train", train), ("validation", validation), ("test", test)]},
        "history_start": str(daily.index.min().date()), "history_end": str(last_day.date()),
        "data_signature": data_signature(signature_data),
        "uncertainty_abs_q90": float(np.quantile(np.abs(errors[winner]), 0.9)),
        "protocol": "Blocos de até sete dias; seleção pelo erro absoluto e quadrático na validação. Teste após treinamento em treino e validação. Modelo final treinado novamente em todos os dias após avaliação.",
        "uncertainty_note": "Faixa estimada com base no percentil 90 do erro absoluto de validação.",
    }
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=model_path.parent, suffix=".tmp")
    os.close(descriptor)
    try:
        joblib.dump({"model": final_model, "metadata": metadata}, temporary)
        os.replace(temporary, model_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    model_path.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    logger.info("Treinamento concluído. Selecionado: %s; MAE validação %.3f kWh/dia.", winner, validation_scores[winner]["mae"])
    return metadata

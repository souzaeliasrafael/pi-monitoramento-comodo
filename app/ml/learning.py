"""Avaliação progressiva persistente: observar, avaliar, treinar e prever.

O replay histórico só é usado na preparação dos dados simulados. O coletor
usa a mesma rotina com o horário de chegada, sem inventar previsões passadas.
"""
import numpy as np
import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from app.database.models import ForecastRecord
from app.ml.features import daily_dataset, training_dataset
from app.ml.train import candidates, fit_model
from app.ml.evaluate import recursive_forecast


def forecast_records(engine):
    with engine.connect() as connection:
        return pd.DataFrame(connection.execute(select(ForecastRecord.__table__).order_by(
            ForecastRecord.issued_at, ForecastRecord.target)).mappings().all())


def learning_step(engine, frame, *, issued_at, seed=42, origin="collector"):
    issued_at = pd.Timestamp(issued_at)
    # A chamada nunca pode acessar leituras que ainda não chegaram.
    available = frame[frame.timestamp <= issued_at]
    if available.dropna(subset=["energy_kwh"]).timestamp.nunique() < 2:
        return 0
    daily = daily_dataset(available)
    complete = daily[daily.consumption_kwh.notna() & (daily.index < issued_at.normalize())]
    if complete.empty:
        return 0
    last = complete.index.max()
    with engine.begin() as connection:
        pending = connection.execute(select(ForecastRecord.__table__).where(ForecastRecord.actual.is_(None))).mappings().all()
        for row in pending:
            target = pd.Timestamp(row["target"])
            if target in complete.index:
                connection.execute(update(ForecastRecord).where(ForecastRecord.id == row["id"]).values(
                    actual=float(complete.loc[target, "consumption_kwh"]), evaluated_at=issued_at.to_pydatetime()))
        previous = connection.execute(select(ForecastRecord.training_end).order_by(ForecastRecord.training_end.desc()).limit(1)).scalar()
    if previous is not None and pd.Timestamp(previous) >= last:
        return 0
    history = daily.loc[:last]
    dataset = training_dataset(history).tail(14)
    if len(dataset) < 14 or history.tail(7).consumption_kwh.isna().any():
        return 0
    model = fit_model(candidates(seed)["RandomForestRegressor"], dataset)
    # Ignora o dia em andamento: todas as previsões salvas são prospectivas.
    offset = (issued_at.normalize() - last).days
    if offset > 23:
        return 0
    predictions = recursive_forecast(model, history, offset + 7)
    predictions = predictions[predictions.timestamp > issued_at.normalize()].head(7)
    ledger = forecast_records(engine)
    spread = None
    if not ledger.empty:
        scored = ledger.dropna(subset=["actual"]).sort_values("issued_at").drop_duplicates("target", keep="last").tail(14)
        if len(scored) >= 3:
            spread = float(np.quantile(abs(scored.actual - scored.prediction), .9))
    with engine.begin() as connection:
        for row in predictions.itertuples():
            connection.execute(insert(ForecastRecord).values(
                issued_at=issued_at.to_pydatetime(), training_end=last.to_pydatetime(),
                target=row.timestamp.to_pydatetime(), prediction=float(row.prediction_kwh),
                spread=spread, origin=origin).on_conflict_do_nothing())
    return len(predictions)


def replay_learning(engine, frame, seed=42):
    """Entrega um dia de cada vez; nenhuma previsão usa observações futuras."""
    arrivals = frame.groupby(frame.timestamp.dt.normalize()).timestamp.min()
    for arrival in arrivals:
        learning_step(engine, frame, issued_at=arrival, seed=seed, origin="historical_replay")
    learning_step(engine, frame, issued_at=frame.timestamp.max(), seed=seed, origin="historical_replay")


def adaptive_forecast(engine, price):
    records = forecast_records(engine)
    if records.empty:
        return None, records
    latest = records[records.issued_at == records.issued_at.max()].copy()
    forecast = pd.DataFrame({"timestamp": latest.target, "prediction_kwh": latest.prediction,
                             "lower_kwh": (latest.prediction - latest.spread).clip(lower=0),
                             "upper_kwh": latest.prediction + latest.spread,
                             "cost_brl": latest.prediction * price})
    return forecast.reset_index(drop=True), records


def forecast_for_period(engine, price, start, end):
    """Consulta previsões prospectivas por dia alvo, sem alterar o treinamento."""
    records = forecast_records(engine)
    if records.empty:
        return None, records
    records = records[(records.target >= pd.Timestamp(start)) &
                      (records.target < pd.Timestamp(end)) &
                      (records.issued_at < records.target)].copy()
    if records.empty:
        return None, records
    latest = records.sort_values("issued_at").drop_duplicates("target", keep="last").sort_values("target")
    forecast = pd.DataFrame({"timestamp": latest.target, "prediction_kwh": latest.prediction,
                             "lower_kwh": (latest.prediction - latest.spread).clip(lower=0),
                             "upper_kwh": latest.prediction + latest.spread,
                             "cost_brl": latest.prediction * price})
    return forecast.reset_index(drop=True), records

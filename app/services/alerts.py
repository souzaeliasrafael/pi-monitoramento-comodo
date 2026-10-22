"""Alertas locais persistentes. Nenhuma mensagem é enviada a terceiros."""

from datetime import timedelta
import logging

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.config import Settings
from app.database.models import AlertRecord

logger = logging.getLogger(__name__)
COOLDOWN = timedelta(hours=6)


def candidates(frame: pd.DataFrame, settings: Settings) -> list[dict]:
    result = []
    rules = [("temperature_c", "TEMPERATURA_ALTA", settings.temperature_max, True, 5),
             ("temperature_c", "TEMPERATURA_BAIXA", settings.temperature_min, False, 5),
             ("humidity_percent", "UMIDADE_ALTA", settings.humidity_max, True, 10),
             ("humidity_percent", "UMIDADE_BAIXA", settings.humidity_min, False, 10)]
    for variable, kind, threshold, high, critical_delta in rules:
        selected = frame[frame[variable] > threshold] if high else frame[frame[variable] < threshold]
        for row in selected.itertuples():
            observed = getattr(row, variable)
            result.append({"timestamp": row.timestamp.to_pydatetime(), "device_id": row.device_id,
                           "type": kind, "level": "CRITICAL" if abs(observed - threshold) >= critical_delta else "WARNING",
                           "message": kind.replace("_", " ").capitalize(), "observed": float(observed), "threshold": float(threshold)})
    for device, meter in frame.dropna(subset=["power_w"]).groupby("device_id"):
        power = meter.sort_values("timestamp").set_index("timestamp").power_w
        rolling = power.rolling("24h", closed="left", min_periods=24)
        limit = pd.concat([rolling.mean() * 1.8, rolling.mean() + 3 * rolling.std()], axis=1).max(axis=1).clip(lower=500)
        for timestamp in power.index[power > limit]:
            observed, threshold = float(power.loc[timestamp]), float(limit.loc[timestamp])
            if not np.isfinite(threshold):
                continue
            result.append({"timestamp": timestamp.to_pydatetime(), "device_id": device,
                           "type": "CONSUMO_ELEVADO", "level": "CRITICAL" if observed > threshold * 1.5 else "WARNING",
                           "message": "Potência acima do padrão das últimas 24 horas", "observed": observed, "threshold": threshold})
    return sorted(result, key=lambda a: (a["timestamp"], a["device_id"], a["type"]))


def detect_alerts(frame: pd.DataFrame, settings: Settings) -> list[dict]:
    emitted, latest = [], {}
    for alert in candidates(frame, settings):
        key = alert["device_id"], alert["type"]
        if key not in latest or alert["timestamp"] - latest[key] >= COOLDOWN:
            emitted.append(alert)
            latest[key] = alert["timestamp"]
    return emitted


def active_alerts(frame: pd.DataFrame, settings: Settings, now=None) -> list[dict]:
    if frame.empty:
        return []
    latest = frame.groupby("device_id").timestamp.max()
    now = pd.Timestamp(now if now is not None else frame.timestamp.max())
    freshness = max(settings.simulation_interval_seconds * 2, 1800)
    return [a for a in candidates(frame, settings)
            if a["timestamp"] == latest[a["device_id"]]
            and 0 <= (now - a["timestamp"]).total_seconds() <= freshness]


def sync_alerts(engine, frame: pd.DataFrame, settings: Settings) -> int:
    count = 0
    with engine.begin() as conn:
        existing = conn.execute(select(AlertRecord.device_id, AlertRecord.type, AlertRecord.timestamp).order_by(AlertRecord.timestamp)).all()
        latest = {(r.device_id, r.type): r.timestamp for r in existing}
        for alert in detect_alerts(frame, settings):
            key = alert["device_id"], alert["type"]
            if key in latest and alert["timestamp"] - latest[key] < COOLDOWN:
                continue
            conn.execute(insert(AlertRecord).values(**alert).on_conflict_do_nothing())
            latest[key] = alert["timestamp"]
            count += 1
    if count:
        logger.info("Alertas registrados: %d", count)
    return count


def load_alerts(engine, start=None, end=None) -> pd.DataFrame:
    statement = select(AlertRecord).order_by(AlertRecord.timestamp.desc())
    if start is not None:
        statement = statement.where(AlertRecord.timestamp >= start)
    if end is not None:
        statement = statement.where(AlertRecord.timestamp < end)
    with engine.connect() as conn:
        return pd.read_sql(statement, conn)

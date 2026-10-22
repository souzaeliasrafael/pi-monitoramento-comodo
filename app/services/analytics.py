"""Análise exploratória e consumo derivado de diferenças do contador."""

import pandas as pd
import plotly.express as px
from app.presentation import device_name

READING_COLUMNS = ["timestamp", "device_id", "temperature_c", "humidity_percent",
                   "voltage_v", "current_a", "power_w", "energy_kwh"]


def readings_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=READING_COLUMNS)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    for col in READING_COLUMNS[2:]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame.sort_values(["timestamp", "device_id"]).reset_index(drop=True)


def filter_readings(frame, start=None, end=None, device_id=None):
    result = frame
    if start is not None:
        result = result[result.timestamp >= pd.Timestamp(start)]
    if end is not None:
        result = result[result.timestamp < pd.Timestamp(end)]
    if device_id is not None:
        result = result[result.device_id == device_id]
    return result.copy()


def environmental_summary(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.groupby("device_id")[["temperature_c", "humidity_percent"]].agg(
        ["mean", "min", "max", "median", "std"]
    ).dropna(how="all")


def hourly_consumption(frame: pd.DataFrame) -> pd.DataFrame:
    """Distribui deltas proporcionalmente às horas atravessadas pelo intervalo.

    Intervalos > 1h e reinícios do contador são excluídos, nunca tratados como
    consumo zero. coverage_hours informa a cobertura observada por medidor.
    """
    pieces, excluded = [], 0
    meters = frame.dropna(subset=["energy_kwh"])
    for device, group in meters.groupby("device_id"):
        records = list(group.sort_values("timestamp").itertuples())
        for previous, current in zip(records, records[1:]):
            start, end = previous.timestamp, current.timestamp
            seconds = (end - start).total_seconds()
            delta = current.energy_kwh - previous.energy_kwh
            if seconds <= 0 or seconds > 3600 or delta < 0:
                excluded += 1
                continue
            cursor = start
            while cursor < end:
                boundary = min(cursor.floor("h") + pd.Timedelta(hours=1), end)
                duration = (boundary - cursor).total_seconds()
                pieces.append((cursor.floor("h"), device, delta * duration / seconds, duration / 3600))
                cursor = boundary
    result = pd.DataFrame(pieces, columns=["timestamp", "device_id", "consumption_kwh", "coverage_hours"])
    if not result.empty:
        result = result.groupby(["timestamp", "device_id"], as_index=False).sum(numeric_only=True)
    result.attrs["excluded_intervals"] = excluded
    return result


def consumption_by_period(frame: pd.DataFrame, frequency: str = "D") -> pd.DataFrame:
    hourly = hourly_consumption(frame)
    if hourly.empty:
        result = pd.DataFrame(columns=["timestamp", "consumption_kwh", "coverage_hours"])
        result.attrs.update(hourly.attrs)
        return result
    result = hourly.set_index("timestamp")[["consumption_kwh", "coverage_hours"]].resample(frequency).sum(min_count=1).reset_index()
    result.attrs.update(hourly.attrs)
    return result


def energy_statistics(frame: pd.DataFrame) -> dict:
    power = frame.power_w.dropna()
    hourly = hourly_consumption(frame)
    peak = None
    if not hourly.empty:
        totals = hourly.groupby(hourly.timestamp.dt.hour)[["consumption_kwh", "coverage_hours"]].sum()
        profile = totals.consumption_kwh / totals.coverage_hours
        peak = int(profile.idxmax())
    return {"mean_power_w": None if power.empty else float(power.mean()),
            "max_power_w": None if power.empty else float(power.max()),
            "peak_hour": peak}


def breaker_activity(frame):
    """Horas ativas estimadas por interpolação entre leituras; lacunas > 1h excluídas."""
    rows = []
    for _, group in frame.dropna(subset=["power_w"]).groupby("device_id"):
        readings = list(group.sort_values("timestamp").itertuples())
        for a, b in zip(readings, readings[1:]):
            seconds = (b.timestamp - a.timestamp).total_seconds()
            if not 0 < seconds <= 3600:
                continue
            weight = (int(a.power_w > .1) + int(b.power_w > .1)) / 2
            cursor = a.timestamp
            while cursor < b.timestamp:
                boundary = min(cursor.normalize() + pd.Timedelta(days=1), b.timestamp)
                hours = (boundary - cursor).total_seconds() / 3600
                rows.append((cursor.normalize(), hours * weight, hours))
                cursor = boundary
    result = pd.DataFrame(rows, columns=["timestamp", "active_hours", "coverage_hours"])
    return result.groupby("timestamp", as_index=False).sum() if not result.empty else result


def time_chart(frame: pd.DataFrame, variable: str, title: str):
    data = frame.dropna(subset=[variable]).copy()
    data["device_id"] = data.device_id.map(device_name)
    figure = px.line(data, x="timestamp", y=variable, color="device_id", title=title,
                   labels={"timestamp": "Horário local", "device_id": "Dispositivo",
                           "temperature_c": "Temperatura (°C)", "humidity_percent": "Umidade (%)",
                           "power_w": "Potência (W)", "voltage_v": "Tensão (V)", "current_a": "Corrente (A)"})
    figure.update_xaxes(tickformat="%d/%m\n%H:%M", hoverformat="%d/%m/%Y %H:%M")
    figure.update_layout(separators=",.", legend_title_text="")
    if variable == "power_w":
        figure.update_traces(line_shape="hv")
    figure.update_yaxes(tickformat=".2f")
    figure.update_traces(hovertemplate="%{x|%d/%m/%Y %H:%M}: %{y:.2f}<extra>%{fullData.name}</extra>")
    return figure


def consumption_chart(frame: pd.DataFrame, frequency="D", start=None, end=None):
    periods = consumption_by_period(frame, frequency)
    if start is not None:
        periods = periods[periods.timestamp >= pd.Timestamp(start)]
    if end is not None:
        periods = periods[periods.timestamp < pd.Timestamp(end)]
    figure = px.bar(periods, x="timestamp", y="consumption_kwh",
                  labels={"timestamp": "Período", "consumption_kwh": "Consumo (kWh)"})
    figure.update_xaxes(tickformat="%d/%m", hoverformat="%d/%m/%Y")
    figure.update_layout(separators=",.")
    figure.update_yaxes(tickformat=".2f")
    figure.update_traces(hovertemplate="%{x|%d/%m/%Y %H:%M}: %{y:.2f}<extra>%{fullData.name}</extra>")
    return figure

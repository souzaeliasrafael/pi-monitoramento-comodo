"""Rótulos em português na interface e nos relatórios, preservando o contrato interno."""

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# Paleta única dos gráficos, alinhada ao tema do Streamlit (.streamlit/config.toml).
PALETTE = ["#2B5A84", "#C8862A", "#5B8C5A", "#8A5A9E", "#B5523B"]
pio.templates["comodo"] = go.layout.Template(layout=go.Layout(
    colorway=PALETTE, font={"family": "Source Sans Pro, Segoe UI, sans-serif", "color": "#1F2933", "size": 13},
    title={"font": {"size": 16, "color": "#1F2933"}, "x": 0, "xanchor": "left"},
    paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
    margin={"l": 56, "r": 16, "t": 56, "b": 48}, hovermode="closest",
    hoverlabel={"bgcolor": "#FFFFFF", "bordercolor": "#D5DCE1", "font": {"color": "#1F2933"}},
    legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1, "title": {"text": ""}},
    xaxis={"gridcolor": "#EEF1F3", "linecolor": "#C9D1D7", "zeroline": False, "title": {"standoff": 8}},
    yaxis={"gridcolor": "#EEF1F3", "linecolor": "#C9D1D7", "zeroline": False, "title": {"standoff": 8}},
    bargap=.28))
pio.templates.default = "plotly_white+comodo"

DEVICES = {"sensor_01": "Sensor 1", "sensor_02": "Sensor 2", "sensor_03": "Sensor 3", "energy_meter_01": "Disjuntor inteligente"}
MODELS = {"Anterior": "Consumo do dia anterior", "Média móvel 7 dias": "Média dos últimos 7 dias",
          "LinearRegression": "Linear Regression", "RandomForestRegressor": "Random Forest",
          "GradientBoostingRegressor": "Gradient Boosting"}
COLUMNS = {"timestamp": "Data e hora", "device_id": "Dispositivo", "temperature_c": "Temperatura (°C)",
           "humidity_percent": "Umidade (%)", "power_w": "Potência (W)", "voltage_v": "Tensão (V)",
           "current_a": "Corrente (A)", "energy_kwh": "Energia acumulada (kWh)",
           "consumption_kwh": "Consumo (kWh)", "coverage_hours": "Cobertura (horas)",
           "cost_brl": "Custo (R$)", "prediction_kwh": "Consumo previsto (kWh)",
           "lower_kwh": "Limite inferior (kWh)", "upper_kwh": "Limite superior (kWh)",
           "type": "Tipo", "level": "Nível", "message": "Descrição", "observed": "Valor observado", "threshold": "Limite"}
STATISTICS = {"mean": "Média", "min": "Mínima", "max": "Máxima", "median": "Mediana", "std": "Desvio padrão"}


def number(value, digits=2):
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def device_name(value):
    return DEVICES.get(value, value)


def localized_table(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.drop(columns=["id"], errors="ignore").copy()
    if "device_id" in result:
        result["device_id"] = result.device_id.map(device_name)
    if "level" in result:
        result["level"] = result.level.replace({"INFO": "Informação", "WARNING": "Atenção", "CRITICAL": "Crítico"})
    if "type" in result:
        result["type"] = result.type.str.replace("_", " ").str.capitalize()
    if "timestamp" in result:
        result["timestamp"] = pd.to_datetime(result.timestamp).dt.strftime("%d/%m/%Y %H:%M")
    for column in result.select_dtypes(include="number").columns:
        result[column] = result[column].map(lambda value: "—" if pd.isna(value) else number(value, 2))
    return result.rename(columns=COLUMNS)


def localized_environment(summary: pd.DataFrame) -> pd.DataFrame:
    result = summary.T.copy()
    result.index = [f"{COLUMNS.get(variable, variable)} — {STATISTICS.get(stat, stat)}" for variable, stat in result.index]
    result.index.name = "Indicador"
    result.columns = [device_name(device) for device in result.columns]
    return result.map(lambda value: "—" if pd.isna(value) else number(value))

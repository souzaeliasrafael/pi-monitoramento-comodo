"""Apresentação das previsões e explicação das métricas."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import local_now
from app.ml.learning import adaptive_forecast, forecast_for_period
from app.dashboard.learning import render_learning
from app.ml.predict import predict_consumption
from app.ml.train import MODEL_PATH
from app.services.analytics import consumption_by_period
from app.presentation import MODELS, number, localized_table


def render_forecast(frame, settings, model_path=MODEL_PATH, engine=None, *, start=None, end=None, show_metrics=True):
    if start is not None and end is not None:
        return render_period_forecast(frame, settings, engine, start, end, show_metrics=show_metrics)
    try:
        forecast, metadata = predict_consumption(frame, settings.energy_price_kwh, model_path=model_path)
    except (ValueError, OSError) as error:
        st.subheader("Previsão energética")
        st.info(str(error))
        return None
    ledger = pd.DataFrame()
    if engine is not None:
        adaptive, ledger = adaptive_forecast(engine, settings.energy_price_kwh)
        if adaptive is not None:
            forecast = adaptive
    winner = metadata["selected_model"]
    scores = metadata["test"][winner]
    if not ledger.empty:
        winner = "RandomForestRegressor"
        scored = ledger.dropna(subset=["actual"]).sort_values("issued_at").drop_duplicates("target", keep="last")
        scores = {"mae": float("nan"), "rmse": float("nan")}
        if not scored.empty:
            errors = scored.actual - scored.prediction
            scores = {"mae": errors.abs().mean(), "rmse": (errors.pow(2).mean()) ** .5}
    if forecast.timestamp.min().date() < local_now().date():
        st.warning("Histórico desatualizado: a previsão começa após o último dia completo disponível. Atualize a coleta para prever o período atual.")
    label = "Modelo de aprendizado contínuo" if not ledger.empty else "Modelo selecionado"
    st.write(f"{label}: **{MODELS.get(winner, winner)}** • Período: **{forecast.timestamp.min():%d/%m/%Y} a {forecast.timestamp.max():%d/%m/%Y}**.")
    st.caption("Previsão atual baseada no histórico completo, independente do filtro de consulta. No aprendizado contínuo, os sete dias começam depois da emissão, sem incluir o dia em andamento.")
    st.caption("O consumo varia conforme os equipamentos e o tempo de uso. Novos dias completos permitem avaliar as previsões anteriores e atualizar o modelo.")
    cards = [*st.columns(2), *st.columns(2)]
    cards[0].metric("Consumo previsto • 7 dias", f"{number(forecast.prediction_kwh.sum())} kWh")
    cards[1].metric("Custo previsto • 7 dias", f"R$ {number(forecast.cost_brl.sum())}")
    error_help = ("O erro absoluto representa o tamanho médio do erro diário. "
                  "O erro quadrático dá mais peso aos erros grandes. Menores valores são melhores; "
                  + ("resultados das previsões anteriores comparadas aos novos dias observados."
                     if not ledger.empty else "resultados do teste temporal reservado."))
    cards[2].metric("Erro absoluto médio", "—" if pd.isna(scores["mae"]) else f"{number(scores['mae'])} kWh/dia", help=error_help)
    cards[3].metric("Erro quadrático médio (raiz)", "—" if pd.isna(scores["rmse"]) else f"{number(scores['rmse'])} kWh/dia", help=error_help)
    st.subheader("Previsão energética")
    daily = consumption_by_period(frame)
    daily = daily[(daily.timestamp < forecast.timestamp.min()) & (daily.coverage_hours >= 23.999)].tail(28)
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=daily.timestamp, y=daily.consumption_kwh, name="Histórico", mode="lines"))
    chart.add_trace(go.Scatter(x=forecast.timestamp, y=forecast.upper_kwh, mode="lines", line={"width": 0}, showlegend=False))
    chart.add_trace(go.Scatter(x=forecast.timestamp, y=forecast.lower_kwh, mode="lines", line={"width": 0}, fill="tonexty", fillcolor="rgba(200,134,42,.15)", name="Faixa de erros observados"))
    chart.add_trace(go.Scatter(x=forecast.timestamp, y=forecast.prediction_kwh, name="Previsão", mode="lines+markers", line={"dash": "dash", "color": "#C8862A"}))
    chart.update_layout(yaxis_title="Consumo diário (kWh)", xaxis_title="Dia", legend={"orientation": "h"})
    chart.update_xaxes(tickformat="%d/%m", hoverformat="%d/%m/%Y")
    chart.update_layout(separators=",.")
    chart.update_yaxes(tickformat=".2f")
    chart.update_traces(hovertemplate="%{x|%d/%m/%Y}: %{y:.2f} kWh<extra>%{fullData.name}</extra>")
    st.plotly_chart(chart, width="stretch", config={"displayModeBar": False}, theme=None)
    st.caption("Faixa atualizada pelos erros das previsões anteriores, após a chegada das leituras. São necessários pelo menos três dias avaliados." if not ledger.empty else "Faixa estimada a partir dos erros observados na validação.")
    st.subheader("Comparação inicial dos modelos")
    rows = []
    for name, validation in metadata["validation"].items():
        test = metadata["test"][name]
        rows.append({"Modelo": MODELS.get(name, name), "Erro absoluto na validação (kWh/dia)": validation["mae"],
                     "Erro quadrático na validação (kWh/dia)": validation["rmse"], "Erro absoluto no teste (kWh/dia)": test["mae"],
                     "Erro quadrático no teste (kWh/dia)": test["rmse"], "Erro percentual no teste (%)": test["mape_percent"]})
    st.table(localized_table(pd.DataFrame(rows)))
    st.caption("Seleção pelo menor erro absoluto na validação, com erro quadrático no desempate. Os modelos de referência também podem vencer. O erro percentual desconsidera consumos iguais a zero.")
    st.caption("Avaliação em blocos de até sete dias. O teste usa treinamento e validação anteriores; depois da avaliação, o modelo final é treinado novamente com todo o histórico.")
    st.table(localized_table(forecast))
    render_learning(ledger)
    return forecast


def render_forecast_metrics(forecast, ledger):
    scored = ledger.dropna(subset=["actual"]).sort_values("issued_at").drop_duplicates("target", keep="last") if not ledger.empty else pd.DataFrame()
    errors = scored.actual - scored.prediction if not scored.empty else pd.Series(dtype=float)
    cards = [*st.columns(2), *st.columns(2)]
    cards[0].metric("Consumo previsto • período", "—" if forecast is None else f"{number(forecast.prediction_kwh.sum())} kWh")
    cards[1].metric("Custo previsto • período", "—" if forecast is None else f"R$ {number(forecast.cost_brl.sum())}")
    help_text = "Erros das previsões comparadas aos dias observados dentro do filtro. O erro absoluto representa o tamanho médio do erro diário. O erro quadrático dá mais peso aos erros grandes. Menores valores são melhores."
    cards[2].metric("Erro absoluto médio", "—" if scored.empty else f"{number(errors.abs().mean())} kWh/dia", help=help_text)
    cards[3].metric("Erro quadrático médio (raiz)", "—" if scored.empty else f"{number(errors.pow(2).mean() ** .5)} kWh/dia", help=help_text)


def render_period_forecast(frame, settings, engine, start, end, *, show_metrics=True):
    if frame.energy_kwh.notna().sum() == 0:
        st.subheader("Previsão energética")
        st.info("O dispositivo selecionado não mede energia. Selecione Todos ou Disjuntor inteligente para consultar previsões.")
        return None
    forecast, ledger = forecast_for_period(engine, settings.energy_price_kwh, start, end)
    if forecast is None:
        st.subheader("Previsão energética")
        st.info("Não há previsões registradas para os dias selecionados. Escolha um período com previsões disponíveis.")
        return None
    if show_metrics:
        render_forecast_metrics(forecast, ledger)
    st.subheader("Previsão energética")
    st.write("Modelo de aprendizado contínuo: **Random Forest**.")
    st.caption("O filtro seleciona os dias previstos, o histórico observado e os erros exibidos. Para cada dia, usamos a última previsão emitida antes de ele começar. Alterar o filtro não modifica o treinamento nem as previsões registradas.")
    st.caption(f"Previsões disponíveis: {forecast.timestamp.min():%d/%m/%Y} a {forecast.timestamp.max():%d/%m/%Y} • {len(forecast)} dias.")
    daily = consumption_by_period(frame)
    daily = daily[(daily.timestamp >= start) & (daily.timestamp < end) & (daily.coverage_hours >= 23.999)]
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=daily.timestamp, y=daily.consumption_kwh, name="Consumo observado", mode="lines+markers"))
    chart.add_trace(go.Scatter(x=forecast.timestamp, y=forecast.upper_kwh, mode="lines", line={"width": 0}, showlegend=False))
    chart.add_trace(go.Scatter(x=forecast.timestamp, y=forecast.lower_kwh, mode="lines", line={"width": 0}, fill="tonexty", fillcolor="rgba(200,134,42,.15)", name="Faixa de erros observados"))
    chart.add_trace(go.Scatter(x=forecast.timestamp, y=forecast.prediction_kwh, name="Previsão registrada", mode="lines+markers", line={"dash": "dash", "color": "#C8862A"}))
    chart.update_layout(yaxis_title="Consumo diário (kWh)", xaxis_title="Dia", legend={"orientation": "h"}, separators=",.")
    chart.update_xaxes(tickformat="%d/%m", hoverformat="%d/%m/%Y", range=[start, end])
    chart.update_yaxes(tickformat=".2f")
    chart.update_traces(hovertemplate="%{x|%d/%m/%Y}: %{y:.2f} kWh<extra>%{fullData.name}</extra>")
    st.plotly_chart(chart, width="stretch", config={"displayModeBar": False}, theme=None)
    st.caption("Cada faixa representa os erros conhecidos na emissão daquela previsão. Dias sem leituras completas ainda não possuem erro calculado.")
    st.table(localized_table(forecast))
    render_learning(ledger)
    return forecast

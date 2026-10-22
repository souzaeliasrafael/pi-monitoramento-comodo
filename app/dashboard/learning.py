"""Visualização do ciclo de previsão e avaliação com novas observações."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from app.presentation import localized_table, number


def render_learning(records):
    if records.empty:
        return
    st.subheader("Aprendizado com novas leituras")
    st.caption("Random Forest é treinado novamente a cada novo dia completo, com até 14 dias de exemplos recentes. Previsões anteriores são preservadas; o erro só é calculado depois da chegada das leituras. O erro pode aumentar ou diminuir.")
    scored = records.dropna(subset=["actual"]).sort_values("issued_at").drop_duplicates("target", keep="last").copy()
    if scored.empty:
        st.info("Aguardando o encerramento dos dias previstos para calcular os erros.")
        return
    scored = scored.sort_values("target")
    scored["error"] = scored.actual - scored.prediction
    st.write(f"Ciclos de treinamento: {records.issued_at.nunique()} • Dias avaliados: {len(scored)} • Erro absoluto médio: {number(scored.error.abs().mean())} kWh/dia")
    chart = go.Figure()
    for field, label in [("prediction", "Previsão registrada"), ("actual", "Consumo observado")]:
        chart.add_trace(go.Scatter(x=scored.target, y=scored[field], name=label, mode="lines+markers", hovertemplate="%{x|%d/%m/%Y}: %{y:.2f} kWh<extra>%{fullData.name}</extra>"))
    chart.update_xaxes(tickformat="%d/%m")
    chart.update_yaxes(title="Consumo diário (kWh)", tickformat=".2f")
    chart.update_layout(separators=",.")
    st.plotly_chart(chart, width="stretch", config={"displayModeBar": False}, theme=None)
    table = pd.DataFrame({"Previsão emitida em": scored.issued_at.dt.strftime("%d/%m/%Y %H:%M"),
                          "Treinamento até": scored.training_end.dt.strftime("%d/%m/%Y"),
                          "Dia previsto": scored.target.dt.strftime("%d/%m/%Y"),
                          "Previsto (kWh)": scored.prediction, "Observado (kWh)": scored.actual,
                          "Erro: observado − previsto (kWh)": scored.error,
                          "Erro absoluto (kWh)": scored.error.abs()})
    st.table(localized_table(table.reset_index(drop=True)))
    st.caption("Uma linha por dia: última previsão emitida antes do início daquele dia. As demais versões permanecem registradas no banco. A faixa futura usa o percentil 90 dos erros absolutos dos últimos 14 dias avaliados, quando há pelo menos três; representa erros observados.")

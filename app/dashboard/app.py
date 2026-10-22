"""Dashboard de monitoramento ambiental e previsão de consumo energético do cômodo."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import datetime, timedelta
import logging

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from app.config import load_settings
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.analytics import (readings_frame, filter_readings, environmental_summary,
                                    time_chart, consumption_chart, consumption_by_period, breaker_activity)
from app.services.alerts import sync_alerts, load_alerts
from app.services.reports import generate_weekly_report
from app.dashboard.forecast import render_forecast
from app.dashboard.equipment import render_equipment
from app.ml.learning import forecast_records, forecast_for_period
from app.services.equipment import list_equipment
from app.logging_config import configure_logging
from app.presentation import device_name, number, localized_table, localized_environment

st.set_page_config(page_title="Monitoramento do cômodo", layout="wide")
# Oculta controles de desenvolvimento do Streamlit que não pertencem ao produto.
st.html('''<style>
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stToolbarActions"] {display:none}
[data-testid="stHeader"] {background:transparent}
[data-testid="stMainBlockContainer"] {padding-top:2.75rem; padding-bottom:3rem; max-width:1280px}

.page-header {display:flex; justify-content:space-between; align-items:flex-end; gap:16px; flex-wrap:wrap;
              border-bottom:1px solid #d5dce1; padding-bottom:14px; margin-bottom:8px}
.page-header .kicker {font-size:.8rem; color:#5f6b75; margin:0 0 2px}
.page-header h1 {font-size:1.85rem; font-weight:700; color:#1f2933; margin:0; padding:0; line-height:1.2}
.page-header .lead {margin:4px 0 0; color:#5f6b75; font-size:.95rem}
.page-header .meta {font-size:.8rem; color:#5f6b75; text-align:right; margin:0}

[data-testid="stSidebar"] {background:#f4f6f8; border-right:1px solid #dde3e8}
.brand {padding:0 2px 14px; margin-bottom:10px; border-bottom:1px solid #d5dce1}
.brand strong {display:block; font-size:1.02rem; color:#1f2933}
.brand span {font-size:.78rem; color:#5f6b75}
[data-testid="stSidebar"] [role="radiogroup"] {gap:2px}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] {width:100%; padding:7px 10px; border-radius:4px; margin:0}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child {display:none}
[data-testid="stSidebar"] label[data-testid="stRadioOption"]:hover {background:#e8ecef}
[data-testid="stSidebar"] label[data-testid="stRadioOption"]:has(input:checked) {background:#e1e7ec}
[data-testid="stSidebar"] label[data-testid="stRadioOption"]:has(input:checked) p {color:#1f2933; font-weight:600}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] p {font-size:.92rem; color:#3e4c59}

[data-testid="stMetric"] {border-radius:6px; padding:0; min-height:100px; background:#fff}
[data-testid="stMetric"] > div {padding:10px 12px}
[data-testid="stMetricLabel"] {min-height:2.4rem; align-items:flex-start}
[data-testid="stMetricLabel"] p {font-size:.8rem; line-height:1.3; white-space:normal; overflow:visible; text-overflow:clip; color:#5f6b75}
[data-testid="stMetricValue"] {font-size:clamp(1.1rem, 2vw, 1.55rem); font-weight:600; color:#1f2933}
.st-key-forecast_cards [data-testid="stMetric"], .st-key-context_cards [data-testid="stMetric"] {background:#f7f8fa}

.section-title {font-size:1.15rem; font-weight:600; color:#1f2933; margin:26px 0 0; padding:0}
.alert-counts {color:#3e4c59; font-size:.9rem; margin:2px 0 8px}
.alert-counts b {color:#1f2933}
[data-testid="stTable"] th {background:#f4f6f8 !important; color:#1f2933 !important; font-weight:600}
</style>''')

PAGES = {
    "Resumo Executivo": ("Resumo executivo", "Ambiente, energia, custos e previsões no período selecionado."),
    "Ambiente e histórico": ("Ambiente e histórico", "Temperatura e umidade registradas pelos três sensores."),
    "Energia": ("Energia", "Consumo diário e potência do circuito medidos pelo disjuntor inteligente."),
    "Alertas": ("Alertas", "Leituras fora dos limites configurados de temperatura, umidade e potência."),
    "Previsão energética": ("Previsão de consumo", "Consumo previsto pelo modelo e comparação com o consumo medido."),
    "Equipamentos": ("Equipamentos", "Cargas elétricas cadastradas no circuito."),
}


def render_header(page, last=None):
    title, lead = PAGES.get(page, (page, ""))
    meta = f'<p class="meta">Última leitura<br>{last:%d/%m/%Y, %H:%M}</p>' if last is not None else ""
    st.html(f'<div class="page-header"><div><p class="kicker">Monitoramento IoT · Mauá/SP</p><h1>{title}</h1>'
            f'<p class="lead">{lead}</p></div>{meta}</div>')


def section(title):
    st.html(f'<h3 class="section-title">{title}</h3>')


def render_sidebar():
    st.sidebar.html('<div class="brand"><strong>Monitoramento do cômodo</strong>'
                    '<span>Projeto Integrador</span></div>')


def money(value):
    return "Sem cobertura suficiente" if value is None else f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_cards(key, metrics):
    with st.container(key=key):
        for offset in range(0, len(metrics), 4):
            columns = st.columns(4, gap="small")
            for column, (label, value, help_text) in zip(columns, metrics[offset:offset + 4]):
                column.metric(label, value, help=help_text, border=True, height="stretch")


def render_dashboard(engine, settings, page="Resumo Executivo"):
    frame = readings_frame(Repository(engine).query())
    if frame.empty:
        render_header(page)
        if page == "Equipamentos":
            render_equipment(engine, settings, show_metrics=False)
            return
        st.info("Banco vazio. Carregue o histórico para visualizar os indicadores.")
        return
    last = frame.timestamp.max()
    render_header(page, last)
    minimum, maximum = frame.timestamp.min().date(), last.date()
    records = forecast_records(engine)
    limit = maximum if records.empty else max(maximum, records.target.max().date())
    with st.container(key="filters"):
        dates = st.columns(3)
        initial = dates[0].date_input("Data inicial", value=max(minimum, maximum - timedelta(days=6)), min_value=minimum, max_value=limit, format="DD/MM/YYYY", key="history_start")
        final = dates[1].date_input("Data final", value=maximum, min_value=minimum, max_value=limit, format="DD/MM/YYYY", key="history_end")
        device = dates[2].selectbox("Dispositivo", ["Todos", *sorted(frame.device_id.unique())], format_func=device_name, key="history_device")
    if initial > final:
        st.info("A data inicial deve ser anterior ou igual à data final.")
        return
    start = datetime.combine(initial, datetime.min.time())
    end = datetime.combine(final + timedelta(days=1), datetime.min.time())
    source = frame if device == "Todos" else frame[frame.device_id == device]
    selected = filter_readings(source, start, end)
    period_frame = selected
    if page == "Equipamentos":
        if device not in ("Todos", "energy_meter_01"):
            st.info("O dispositivo selecionado não possui equipamentos elétricos cadastrados. Selecione Todos ou Disjuntor inteligente.")
        else:
            render_equipment(engine, settings, end=end, show_metrics=False)
        return
    if page == "Previsão energética":
        forecast = render_forecast(source, settings, engine=engine, start=start, end=end, show_metrics=False)
        alerts = load_alerts(engine, start, end)
        if device != "Todos" and not alerts.empty:
            alerts = alerts[alerts.device_id == device]
        render_report(source, settings, alerts, forecast, start, end, device)
        return
    # Agregar antes de filtrar preserva o delta que atravessa o início do período.
    daily = consumption_by_period(source)
    daily = daily[(daily.timestamp >= start) & (daily.timestamp < end)]
    complete = daily[daily.coverage_hours >= 23.999]
    consumption = float(daily.consumption_kwh.sum()) if daily.coverage_hours.sum() > 0 else None
    cost = None if consumption is None else consumption * settings.energy_price_kwh
    monthly = None if complete.empty else float(complete.consumption_kwh.mean() * pd.Timestamp(final).days_in_month * settings.energy_price_kwh)
    sync_alerts(engine, frame, settings)
    alerts = load_alerts(engine, start, end)
    if device != "Todos" and not alerts.empty:
        alerts = alerts[alerts.device_id == device]
    temperature, humidity = selected.temperature_c.mean(), selected.humidity_percent.mean()
    power = period_frame.power_w.mean()
    if page == "Resumo Executivo":
        meter = period_frame.dropna(subset=["power_w"])
        activity = breaker_activity(source)
        activity = activity[(activity.timestamp >= start) & (activity.timestamp < end) & (activity.coverage_hours >= 23.999)]
        forecast, ledger = forecast_for_period(engine, settings.energy_price_kwh, start, end) if device in ("Todos", "energy_meter_01") else (None, pd.DataFrame())
        scored = ledger.dropna(subset=["actual"]).sort_values("issued_at").drop_duplicates("target", keep="last") if not ledger.empty else pd.DataFrame()
        errors = scored.actual - scored.prediction if not scored.empty else pd.Series(dtype=float)
        equipment = [item for item in list_equipment(engine) if item["active_from"] < end]
        total_power = settings.lamp_count * settings.lamp_power_w + sum(item["quantity"] * item["power_w"] for item in equipment)
        section("Dados observados")
        st.caption("Leituras e indicadores do histórico dentro dos filtros.")
        render_cards("observed_cards", [
            ("Temperatura média do período", "—" if pd.isna(temperature) else f"{number(temperature)} °C", None),
            ("Umidade média do período", "—" if pd.isna(humidity) else f"{number(humidity)} %", None),
            ("Consumo do período", "—" if consumption is None else f"{number(consumption)} kWh", None),
            ("Potência média do período", "—" if pd.isna(power) else f"{number(power)} W", "Média da potência total do circuito registrada pelo disjuntor."),
            ("Consumo médio por dia completo", "—" if complete.empty else f"{number(complete.consumption_kwh.mean())} kWh", None),
            ("Alertas no período", len(alerts), None),
            ("Tensão média", "—" if meter.empty else f"{number(meter.voltage_v.mean())} V", None),
            ("Corrente média", "—" if meter.empty else f"{number(meter.current_a.mean())} A", None),
            ("Pico de potência", "—" if meter.empty else f"{number(meter.power_w.max())} W", None),
        ])
        section("Previsões e estimativas")
        st.caption("Resultados do modelo e cálculos de custo ou duração; não são leituras diretas.")
        render_cards("forecast_cards", [
            ("Consumo previsto • período", "—" if forecast is None else f"{number(forecast.prediction_kwh.sum())} kWh", "Última previsão registrada antes do início de cada dia consultado."),
            ("Custo previsto • período", "—" if forecast is None else money(forecast.cost_brl.sum()), "Consumo previsto multiplicado pela tarifa configurada."),
            (f"Projeção mensal • {final:%m/%Y}", money(monthly), "Consumo médio dos dias completos do filtro × dias do mês da data final × tarifa. Dias parciais são excluídos."),
            ("Custo do período", money(cost), "Estimativa calculada a partir do consumo observado e da tarifa configurada."),
            ("Custo médio por dia completo", money(None if complete.empty else complete.consumption_kwh.mean() * settings.energy_price_kwh), "Estimativa de custo médio dos dias com cobertura completa."),
            ("Atividade média por dia", "—" if activity.empty else f"{number(activity.active_hours.mean())} h", "Duração estimada por interpolação entre leituras. Considera dias completos e exclui intervalos acima de uma hora."),
        ])
        section("Validação e equipamentos")
        error_help = "Erros das previsões comparadas aos dias observados dentro do filtro. O erro absoluto representa o tamanho médio do erro diário; o quadrático dá mais peso aos erros grandes. Menores valores são melhores."
        render_cards("context_cards", [
            ("Erro absoluto médio", "—" if scored.empty else f"{number(errors.abs().mean())} kWh/dia", error_help),
            ("Erro quadrático médio (raiz)", "—" if scored.empty else f"{number(errors.pow(2).mean() ** .5)} kWh/dia", error_help),
            ("Potência total se todos estiverem ligados", f"{number(total_power)} W" if device in ("Todos", "energy_meter_01") else "—", "Soma das potências nominais dos equipamentos cadastrados até a data final; não é uma leitura do disjuntor."),
        ])
        st.caption(f"Cobertura do período: {number(daily.coverage_hours.sum())} horas. Tarifa: R$ {number(settings.energy_price_kwh)}/kWh (arredondada apenas na exibição).")
        st.caption("Referência tarifária: Enel São Paulo • Residencial convencional • Vigência desde 04/07/2026. Tarifa configurável conforme a conta de energia.")
        return
    if page == "Ambiente e histórico":
        variable = st.selectbox("Variável do gráfico histórico", ["Temperatura", "Umidade", "Potência"], key="history_variable")
        variable_key = {"Temperatura": "temperature_c", "Umidade": "humidity_percent", "Potência": "power_w"}[variable]
        st.plotly_chart(time_chart(selected, variable_key, "Histórico filtrado e comparação entre sensores"), width="stretch", config={"displayModeBar": False}, theme=None)
        st.subheader("Estatísticas do período filtrado")
        st.table(localized_environment(environmental_summary(selected)))
    elif page == "Energia":
        st.plotly_chart(consumption_chart(source, start=start, end=end), width="stretch", config={"displayModeBar": False}, theme=None)
        st.plotly_chart(time_chart(period_frame, "power_w", "Potência"), width="stretch", config={"displayModeBar": False}, theme=None)
    elif page == "Alertas":
        st.subheader("Ocorrências")
        st.caption("Limites estritos; uma ocorrência por dispositivo/tipo a cada 6 horas. Potência comparada às 24 horas anteriores.")
        if alerts.empty:
            st.success("Nenhum alerta no período selecionado.")
        else:
            levels = alerts.level.value_counts()
            st.html(f'<p class="alert-counts">Total: <b>{len(alerts)}</b> · Críticos: <b>{int(levels.get("CRITICAL", 0))}</b>'
                    f' · Atenção: <b>{int(levels.get("WARNING", 0))}</b></p>')
            st.dataframe(localized_table(alerts), hide_index=True, width="stretch", height=480)


def render_report(frame, settings, alerts, forecast, start, end, device):
    st.subheader("Relatório do período")
    st.caption("Usa as datas e o dispositivo do filtro único. Arquivo HTML independente de internet.")
    selection = (start, end, device)
    if st.button("Gerar relatório do período"):
        report = generate_weekly_report(frame, alerts, settings, forecast=forecast, start=start, end=end)
        st.session_state["report_html"] = report.read_text(encoding="utf-8")
        st.session_state["report_selection"] = selection
        st.success(f"Relatório salvo em reports/{report.name}")
    if st.session_state.get("report_selection") == selection:
        st.download_button("Baixar relatório HTML", st.session_state["report_html"], "relatorio_periodo.html", "text/html")


def main():
    engine = None
    try:
        configure_logging()
        settings = load_settings()
        engine = create_database_engine(settings)
        initialize_database(engine)
        render_sidebar()
        page = st.sidebar.radio("Navegação", ["Resumo Executivo", "Ambiente e histórico", "Energia", "Alertas", "Previsão energética", "Equipamentos"])
        render_dashboard(engine, settings, page)
    except (ValueError, OSError, SQLAlchemyError):
        logging.getLogger(__name__).error("Dashboard indisponível: verifique configuração, dados e banco.")
        st.error("Não foi possível carregar os dados. Verifique o arquivo .env, as permissões do banco e execute a inicialização.")
    except Exception:
        logging.getLogger(__name__).error("Falha inesperada no dashboard; nenhum conteúdo sensível foi registrado.")
        st.error("Ocorreu um erro ao montar a página. Execute os testes e confira as instruções do README.")
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()

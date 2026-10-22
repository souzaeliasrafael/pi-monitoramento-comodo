"""Relatório semanal HTML autossuficiente, sem recursos remotos."""

from html import escape
from pathlib import Path
import logging

import pandas as pd

from app.config import Settings, PROJECT_ROOT, local_now
from app.services.analytics import filter_readings, consumption_by_period
from app.services.energy import energy_summary
from app.presentation import localized_table, number

logger = logging.getLogger(__name__)


def environmental_section(frame, variable, minimum, maximum, label, unit):
    values = frame[variable].dropna()
    if values.empty:
        return f"<h2>{label}</h2><p>Sem dados no período.</p>"
    out = int(((values < minimum) | (values > maximum)).sum())
    return (f"<h2>{label}</h2><p>Média: {number(values.mean())} {unit} · Mínima: {number(values.min())} {unit} · "
            f"Máxima: {number(values.max())} {unit}</p><p>Leituras fora da faixa: {out} de {len(values)}. "
            "Uma condição prolongada pode corresponder a várias leituras.</p>")


def generate_weekly_report(frame, alerts, settings: Settings, *, end=None, start=None,
                           forecast=None, output_dir: Path = PROJECT_ROOT / "reports") -> Path:
    """Analisa [end - 7 dias, end); padrão: sete dias anteriores à data atual."""
    end = pd.Timestamp(end if end is not None else local_now()).normalize()
    custom_period = start is not None
    start = pd.Timestamp(start).normalize() if custom_period else end - pd.Timedelta(days=7)
    days = (end - start).days
    if days <= 0:
        raise ValueError("O período do relatório deve conter pelo menos um dia.")
    selected = filter_readings(frame, start, end)
    daily = consumption_by_period(frame)
    daily = daily[(daily.timestamp >= start) & (daily.timestamp < end)]
    total = float(daily.consumption_kwh.sum())
    coverage = float(daily.coverage_hours.sum())
    recent_alerts = alerts.copy()
    if not recent_alerts.empty:
        recent_alerts = recent_alerts[(recent_alerts.timestamp >= start) & (recent_alerts.timestamp < end)]
    complete = daily[daily.coverage_hours >= 23.999]
    monthly = (None if complete.empty else float(complete.consumption_kwh.mean() * (end - pd.Timedelta(days=1)).days_in_month * settings.energy_price_kwh)) if custom_period else energy_summary(frame, settings.energy_price_kwh, end)["estimated_month_cost"]
    monthly_text = "indisponível" if monthly is None else f"R$ {number(monthly)}"
    alert_html = "<p>Nenhum alerta registrado no período.</p>"
    if not recent_alerts.empty:
        types = localized_table(recent_alerts).groupby("Tipo").size().rename("Quantidade").to_frame()
        alert_html = types.to_html(escape=True) + localized_table(recent_alerts[["timestamp", "device_id", "type", "level", "observed", "threshold"]].head(20)).to_html(index=False, escape=True)
    forecast_html = "<p>Previsão ainda indisponível. Treine o modelo e gere a previsão.</p>"
    if forecast is not None and not forecast.empty:
        forecast_html = (f"<p>Período previsto: {forecast.timestamp.min():%d/%m/%Y} a {forecast.timestamp.max():%d/%m/%Y}. "
                         f"Consumo: {number(forecast.prediction_kwh.sum())} kWh · Custo: R$ {number(forecast.cost_brl.sum())}.</p>"
                         + localized_table(forecast).to_html(index=False, escape=True))
    average = total / days
    peak = "indisponível" if daily.empty else f"{number(daily.consumption_kwh.max())} kWh"
    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório do período IoT</title><style>
body{{font:16px/1.6 system-ui,sans-serif;color:#183442;max-width:1050px;margin:40px auto;padding:0 24px}}
h1,h2{{color:#147D92}} .notice{{background:#edf6f8;padding:16px;border-left:4px solid #147D92}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:16px 0}}th,td{{padding:8px;border:1px solid #ccd8de;text-align:left}}
@media print{{body{{margin:0}}h2{{break-after:avoid}}tr{{break-inside:avoid}}}}
</style></head><body><h1>Relatório {'do período' if custom_period else 'semanal'} do cômodo</h1>
<p class="notice">Período: {start:%d/%m/%Y} até {(end - pd.Timedelta(days=1)):%d/%m/%Y}, em horário de Brasília.</p>
{environmental_section(selected, 'temperature_c', settings.temperature_min, settings.temperature_max, 'Temperatura', '°C')}
{environmental_section(selected, 'humidity_percent', settings.humidity_min, settings.humidity_max, 'Umidade', '%')}
<h2>Energia</h2><p>Consumo observado: {number(total)} kWh · Média por dia do período: {number(average)} kWh · Maior consumo diário: {peak}.</p>
<p>Custo estimado: R$ {number(total * settings.energy_price_kwh)} · Tarifa: R$ {number(settings.energy_price_kwh)}/kWh · Projeção mensal: {monthly_text}.</p>
<p>Iluminação inicial: {settings.lamp_count} lâmpadas LED de {number(settings.lamp_power_w)} W, circuito acompanhado por disjuntor inteligente, com acionamentos variáveis e média de 8 a 10 horas nos dias úteis, uso aos sábados até as 12h e consumo zerado aos domingos.
Referência residencial convencional Enel São Paulo, vigente desde 04/07/2026. Custo dos equipamentos monitorados do cômodo,
sem tributos, bandeiras ou cobranças mínimas da residência.</p>
<p>Cobertura: {number(coverage)} de {days * 24} horas esperadas para o disjuntor inteligente. Lacunas não equivalem a consumo zero.
Projeção mensal baseada nos dias completos {'do período selecionado' if custom_period else 'dos últimos 7 dias disponíveis'}, sem impostos.</p>
{localized_table(daily).to_html(index=False, escape=True)}
<h2>Alertas</h2><p>Total de ocorrências agrupadas: {len(recent_alerts)}. Intervalo mínimo de 6 horas por dispositivo/tipo.</p>{alert_html}
<h2>Previsão de consumo</h2>{forecast_html}
<p>Gerado em {local_now():%d/%m/%Y %H:%M:%S}. Sistema IoT acadêmico.</p></body></html>"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"semanal_{end:%Y%m%d}_{local_now():%H%M%S%f}.html"
    path.write_text(html, encoding="utf-8")
    logger.info("Relatório semanal gerado: %s", path.name)
    return path

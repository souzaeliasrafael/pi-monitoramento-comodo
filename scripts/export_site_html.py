"""Exporta uma cópia navegável do painel, com dados e gráficos incorporados."""
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import pandas as pd
from plotly.offline import get_plotlyjs

from app.config import PROJECT_ROOT, load_settings, local_now
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.services.analytics import readings_frame, consumption_by_period
from app.services.alerts import load_alerts
from app.services.equipment import list_equipment
from app.ml.learning import adaptive_forecast
from app.ml.predict import load_model, predict_consumption
from app.presentation import MODELS


def records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso", double_precision=10))


def build_payload(settings):
    """Reúne leituras, consumo, alertas e previsões para as páginas exportadas."""
    engine = create_database_engine(settings)
    try:
        initialize_database(engine)
        frame = readings_frame(Repository(engine).query())
        if frame.empty:
            raise ValueError("O banco está vazio; não há dados para exportar.")
        forecast, ledger = adaptive_forecast(engine, settings.energy_price_kwh)
        metadata = load_model()["metadata"]
        if forecast is None:
            forecast, metadata = predict_consumption(frame, settings.energy_price_kwh)
        scored = ledger.dropna(subset=["actual"]).sort_values("issued_at").drop_duplicates("target", keep="last").sort_values("target") if not ledger.empty else ledger
        payload = {"readings": records(frame), "daily": records(consumption_by_period(frame)),
                   "alerts": records(load_alerts(engine)), "forecast": records(forecast), "scored": records(scored),
                   "equipment": records(pd.DataFrame(list_equipment(engine))), "cycles": int(ledger.issued_at.nunique()) if not ledger.empty else 0,
                   "models": [{"name": MODELS.get(name, name), "validation": score, "test": metadata["test"][name]}
                              for name, score in metadata["validation"].items()],
                   "model": "Random Forest" if not ledger.empty else MODELS.get(metadata["selected_model"], metadata["selected_model"]),
                   "price": settings.energy_price_kwh, "lampCount": settings.lamp_count, "lampPower": settings.lamp_power_w,
                   "usageMin": settings.usage_hours_min, "usageMax": settings.usage_hours_max,
                   "generatedAt": local_now().isoformat(),
                   "limits": {"temperature_c": [settings.temperature_min, settings.temperature_max],
                              "humidity_percent": [settings.humidity_min, settings.humidity_max]}}
        return payload
    finally:
        engine.dispose()


def export_site(output):
    payload = build_payload(load_settings())
    template = (PROJECT_ROOT / "app/dashboard/site_export.html").read_text(encoding="utf-8")
    content = template.replace("__DATA__", json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c"))
    content = content.replace("__PLOTLY__", get_plotlyjs())
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "exports/monitoramento_comodo.html")
    print(export_site(parser.parse_args().output))

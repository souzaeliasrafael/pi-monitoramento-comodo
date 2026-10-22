"""Gera a página leve de consulta para compartilhar por link (gráficos via CDN)."""
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json

from app.config import PROJECT_ROOT, load_settings
from scripts.export_site_html import build_payload

READING_FIELDS = ("timestamp", "device_id", "temperature_c", "humidity_percent", "power_w")


def compact(row, fields=None, digits=3):
    """Mantém só os campos usados na página e arredonda números para reduzir o arquivo."""
    keys = fields or row.keys()
    return {key: round(row[key], digits) if isinstance(row.get(key), float) else row.get(key) for key in keys}


def export_share_page(output):
    data = build_payload(load_settings())
    payload = {"readings": [compact(row, READING_FIELDS, 2) for row in data["readings"]],
               "daily": [compact(row, ("timestamp", "consumption_kwh", "coverage_hours")) for row in data["daily"]],
               "alerts": [compact(row, ("timestamp", "device_id", "type", "level", "observed", "threshold"), 2) for row in data["alerts"]],
               "forecast": [compact(row, ("timestamp", "prediction_kwh", "lower_kwh", "upper_kwh", "cost_brl")) for row in data["forecast"]],
               "scored": [compact(row, ("target", "prediction", "actual")) for row in data["scored"]],
               "model": data["model"], "price": data["price"], "limits": data["limits"], "generatedAt": data["generatedAt"]}
    template = (PROJECT_ROOT / "app/dashboard/share_page.html").read_text(encoding="utf-8")
    content = template.replace("__DATA__", json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\u003c"))
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "exports/monitoramento_compartilhar.html")
    print(export_share_page(parser.parse_args().output))

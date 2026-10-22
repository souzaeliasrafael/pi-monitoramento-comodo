from dataclasses import asdict
from datetime import datetime

import pandas as pd

from app.config import Settings
from app.data_sources.simulator import SimulatorDataSource
from app.services.analytics import readings_frame
from app.services.reports import generate_weekly_report


def test_report_populated_and_empty(tmp_path):
    frame = readings_frame([asdict(r) for b in SimulatorDataSource().history(datetime(2026, 1, 1), 7) for r in b])
    path = generate_weekly_report(frame, pd.DataFrame(), Settings(), end=datetime(2026, 1, 8), output_dir=tmp_path)
    html = path.read_text(encoding="utf-8")
    assert "168,00 de 168" in html
    assert "SIMULADOS" not in html
    assert "01/01/2026 até 07/01/2026" in html
    filtered = generate_weekly_report(frame, pd.DataFrame(), Settings(), start=datetime(2026, 1, 3), end=datetime(2026, 1, 5), output_dir=tmp_path)
    filtered_html = filtered.read_text(encoding="utf-8")
    assert "03/01/2026 até 04/01/2026" in filtered_html
    assert "48,00 de 48" in filtered_html
    assert "do período selecionado" in filtered_html
    path = generate_weekly_report(readings_frame([]), pd.DataFrame(), Settings(), output_dir=tmp_path)
    assert "Sem dados no período" in path.read_text(encoding="utf-8")

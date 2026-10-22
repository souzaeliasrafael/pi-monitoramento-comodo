from datetime import datetime
import pandas as pd

from app.presentation import localized_table, localized_environment
from app.services.analytics import readings_frame, environmental_summary


def test_labels_and_severity_in_portuguese():
    result = localized_table(pd.DataFrame([{"timestamp": datetime(2026, 10, 4), "device_id": "energy_meter_01", "level": "WARNING", "type": "CONSUMO_ELEVADO", "observed": 18.0}]))
    assert result.iloc[0]["Dispositivo"] == "Disjuntor inteligente"
    assert result.iloc[0]["Nível"] == "Atenção"
    assert result.iloc[0]["Data e hora"] == "04/10/2026 00:00"
    assert result.iloc[0]["Valor observado"] == "18,00"
    frame = readings_frame([{"timestamp": datetime(2026, 10, 4), "device_id": "sensor_01", "temperature_c": 22, "humidity_percent": 60}])
    assert "Temperatura (°C) — Média" in localized_environment(environmental_summary(frame)).index

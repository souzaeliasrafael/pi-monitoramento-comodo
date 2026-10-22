"""Contrato de leitura: horários locais sem offset (America/Sao_Paulo)."""

from dataclasses import dataclass
from datetime import datetime
import math


@dataclass(frozen=True)
class Reading:
    timestamp: datetime
    device_id: str
    temperature_c: float | None = None
    humidity_percent: float | None = None
    voltage_v: float | None = None
    current_a: float | None = None
    power_w: float | None = None
    energy_kwh: float | None = None

    def validate(self) -> None:
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is not None:
            raise ValueError("Timestamp deve ser datetime local sem offset.")
        if not self.device_id or len(self.device_id) > 100:
            raise ValueError("Identificador de dispositivo inválido.")
        values = (self.temperature_c, self.humidity_percent, self.voltage_v,
                  self.current_a, self.power_w, self.energy_kwh)
        if any(v is not None and not math.isfinite(v) for v in values):
            raise ValueError("Leitura contém valor não finito.")
        environmental = self.temperature_c is not None and self.humidity_percent is not None
        electrical = all(v is not None for v in values[2:])
        if environmental == electrical:
            raise ValueError("Informe uma leitura ambiental OU elétrica completa.")
        if environmental:
            if any(v is not None for v in values[2:]):
                raise ValueError("Leitura ambiental com campos elétricos.")
            if not -40 <= self.temperature_c <= 85 or not 0 <= self.humidity_percent <= 100:
                raise ValueError("Temperatura/umidade fisicamente inválida.")
        else:
            if self.temperature_c is not None or self.humidity_percent is not None:
                raise ValueError("Leitura elétrica com campos ambientais.")
            if not 80 <= self.voltage_v <= 260 or min(values[3:]) < 0:
                raise ValueError("Leitura elétrica fisicamente inválida.")


"""Dispositivos inteiramente simulados; não representam medições reais."""

from datetime import datetime, timedelta
import math

from app.data_sources.readings import Reading
from app.data_sources.base import DataSource
from app.config import local_now, Settings
from app.services.lighting import lighting_power, lighting_energy
from app.services.equipment import equipment_load
from app.data_sources.climate import temperature_reference


class SimulatorDataSource(DataSource):
    def __init__(self, seed: int = 42, initial_time: datetime | None = None,
                 initial_energy_kwh: float = 0, initial_power_w: float | None = None,
                 settings: Settings | None = None, equipment_provider=None):
        self.settings = settings or Settings(simulation_seed=seed)
        self.seed = seed
        self.last_time = initial_time
        self.total = initial_energy_kwh
        self.last_power = initial_power_w
        self.equipment_provider = equipment_provider

    def get_current_readings(self, timestamp: datetime | None = None) -> list[Reading]:
        t = timestamp or local_now()
        if t.tzinfo is not None or (self.last_time and t < self.last_time):
            raise ValueError("Simulação exige horários locais em ordem crescente.")
        hour = t.hour + t.minute / 60 + t.second / 3600
        day = t.toordinal()
        phase = self.seed * 0.137
        daily = math.sin(2 * math.pi * (hour - 9) / 24)
        continuous_day = day + hour / 24
        weather = 1.7 * math.sin(continuous_day * 0.61 + phase) + 0.8 * math.sin(continuous_day * 0.27)
        event = max(0, math.sin(math.pi * (hour - 12) / 6)) if 12 < hour < 18 and day % 17 == 0 else 0
        low, high = temperature_reference(t)
        # Hipótese de ambiente interno: +1 °C e amplitude diária 20% menor que no exterior.
        temperature = (low + high) / 2 + 1 + (high - low) / 2 * 0.8 * daily + weather + 5.5 * event
        rows = []
        for i in range(3):
            noise = 0.22 * math.sin((day * 24 + hour) * 2.1 + phase + i)
            temp = temperature + (i - 1) * 0.8 + noise
            # Relação sintética, não uma série de umidade observada em Mauá.
            humidity = max(30, min(95, 72 - 2.2 * (temp - 20) + 3 * math.sin(continuous_day * 0.31 + i)))
            rows.append(Reading(t, f"sensor_{i + 1:02}", round(temp, 3), round(humidity, 3)))
        equipment = self.equipment_provider() if self.equipment_provider else []
        extra_power, extra_energy = equipment_load(equipment, self.last_time or t, t, seed=self.settings.simulation_seed,
                                                   minimum=self.settings.usage_hours_min, maximum=self.settings.usage_hours_max)
        power = lighting_power(t, self.settings)
        power += extra_power
        voltage = 220 + 3 * math.sin(day * .37 + phase) + 1.5 * math.sin(hour / 2 + phase) + .6 * math.sin(hour * 9.3 + day)
        if self.last_time is not None:
            self.total += lighting_energy(self.last_time, t, self.settings)
            self.total += extra_energy
        self.last_time, self.last_power = t, power
        rows.append(Reading(t, "energy_meter_01", voltage_v=voltage,
                            current_a=power / voltage, power_w=power, energy_kwh=self.total))
        return rows

    def history(self, start: datetime, days: int, interval_minutes: int = 15):
        """Inclui a fronteira final; o primeiro total é a referência de consumo zero."""
        if days <= 0 or interval_minutes <= 0 or interval_minutes > 60:
            raise ValueError("Dias > 0 e intervalo entre 1 e 60 minutos são necessários.")
        end = start + timedelta(days=days)
        t = start
        while t < end:
            yield self.get_current_readings(t)
            t = min(t + timedelta(minutes=interval_minutes), end)
        yield self.get_current_readings(end)

    def history_by_count(self, start: datetime, end: datetime, records: int):
        """Quantidade exata de leituras, em lotes completos dos quatro dispositivos."""
        if records < 8 or records % 4:
            raise ValueError("Registros devem ser múltiplo de quatro, com mínimo de oito.")
        points = records // 4
        duration = end - start
        if duration.total_seconds() <= 0 or duration / (points - 1) > timedelta(hours=1):
            raise ValueError("Período inválido ou registros insuficientes para intervalos de até uma hora.")
        for index in range(points):
            yield self.get_current_readings(start + duration * index / (points - 1))


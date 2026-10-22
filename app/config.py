"""Configuração validada; importar este módulo não cria banco nem arquivos."""

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def local_now() -> datetime:
    """Horário de referência único, independente do fuso do computador."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///data/monitoramento.db"
    simulation_interval_seconds: float = 60
    energy_price_kwh: float = 0.78938
    lamp_count: int = 4
    lamp_power_w: float = 15
    usage_hours_min: float = 8
    usage_hours_max: float = 10
    temperature_min: float = 18
    temperature_max: float = 30
    humidity_min: float = 40
    humidity_max: float = 70
    data_source: str = "simulator"
    simulation_seed: int = 42
    tuya_access_id: str = field(default="", repr=False)
    tuya_access_secret: str = field(default="", repr=False)
    tuya_endpoint: str = ""
    tuya_device_ids: str = ""

    def __post_init__(self) -> None:
        if self.data_source not in {"simulator", "tuya"}:
            raise ValueError("DATA_SOURCE deve ser simulator ou tuya.")
        if not isinstance(self.simulation_seed, int):
            raise ValueError("SIMULATION_SEED deve ser inteiro.")
        if not isinstance(self.lamp_count, int) or self.lamp_count < 1:
            raise ValueError("LAMP_COUNT deve ser inteiro positivo.")
        if not all(math.isfinite(v) for v in (self.usage_hours_min, self.usage_hours_max)) or not 0 < self.usage_hours_min <= self.usage_hours_max <= 12:
            raise ValueError("A faixa de atividade diária deve estar entre zero e 12 horas.")
        if not 0 < self.lamp_power_w <= 100:
            raise ValueError("A potência das lâmpadas deve ser positiva e até 100 W.")
        for name in (
            "simulation_interval_seconds", "energy_price_kwh",
            "temperature_min", "temperature_max", "humidity_min", "humidity_max",
        ):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name.upper()} deve ser um número finito.")
        if self.simulation_interval_seconds <= 0:
            raise ValueError("SIMULATION_INTERVAL_SECONDS deve ser positivo.")
        if self.energy_price_kwh < 0:
            raise ValueError("ENERGY_PRICE_KWH não pode ser negativo.")
        if self.temperature_min >= self.temperature_max:
            raise ValueError("TEMPERATURE_MIN deve ser menor que TEMPERATURE_MAX.")
        if not 0 <= self.humidity_min < self.humidity_max <= 100:
            raise ValueError("A faixa de umidade deve estar entre 0 e 100, com mínimo < máximo.")
        try:
            url = make_url(self.database_url)
        except ArgumentError:
            raise ValueError("DATABASE_URL deve ser uma URL SQLite válida.") from None
        if url.drivername not in {"sqlite", "sqlite+pysqlite"} or not url.database:
            raise ValueError("DATABASE_URL deve indicar um arquivo SQLite ou :memory:.")
        if url.host or url.username or url.password or url.port or url.query:
            raise ValueError("Use uma URL SQLite simples, sem credenciais ou parâmetros.")


def load_settings(env_file: Path | None = None) -> Settings:
    """Lê padrões < arquivo .env < variáveis do processo, sem alterar os.environ."""
    values = dotenv_values(env_file if env_file is not None else PROJECT_ROOT / ".env")
    defaults = Settings()
    parsed: dict[str, str | float] = {}
    for name in Settings.__dataclass_fields__:
        key = name.upper()
        value = os.environ.get(key, values.get(key))
        if value is None:
            parsed[name] = getattr(defaults, name)
        elif isinstance(getattr(defaults, name), str):
            parsed[name] = value
        elif name in {"simulation_seed", "lamp_count"}:
            try:
                parsed[name] = int(value)
            except ValueError:
                raise ValueError(f"{key} deve ser inteiro.") from None
        else:
            try:
                parsed[name] = float(value)
            except ValueError:
                raise ValueError(f"{key} deve ser numérico.") from None
    return Settings(**parsed)


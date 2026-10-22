"""Validação por leitura e persistência em lotes."""

from datetime import datetime
import logging

from app.data_sources.base import DataSource
from app.data_sources.simulator import SimulatorDataSource
from app.database.repository import Repository
from app.config import Settings

logger = logging.getLogger(__name__)


def persist_batch(repository: Repository, readings: list) -> int:
    valid = []
    for reading in readings:
        try:
            reading.validate()
            valid.append(reading)
        except (ValueError, TypeError, AttributeError):
            logger.warning("Leitura inválida descartada; verifique a fonte de dados.")
    count = repository.insert_readings(valid)
    logger.debug("Leituras inseridas: %d", count)
    return count


def collect_once(source: DataSource, repository: Repository) -> int:
    return persist_batch(repository, source.get_current_readings())


def resume_simulator(source: DataSource, repository: Repository) -> None:
    """Restaura o contador do simulador, sem acoplar os demais serviços à fonte."""
    if isinstance(source, SimulatorDataSource):
        last = repository.latest("energy_meter_01")
        if last:
            source.last_time = last["timestamp"]
            source.total = last["energy_kwh"]
            source.last_power = last["power_w"]


def generate_history(repository: Repository, start: datetime, days: int,
                     seed: int = 42, interval_minutes: int = 15, settings: Settings | None = None,
                     equipment_provider=None) -> int:
    last = repository.latest("energy_meter_01")
    if last and start < last["timestamp"]:
        raise ValueError("Histórico sobreposto. Use um banco novo ou início após o último registro.")
    source = SimulatorDataSource(seed, settings=settings, equipment_provider=equipment_provider)
    resume_simulator(source, repository)
    count, pending = 0, []
    for batch in source.history(start, days, interval_minutes):
        pending.extend(batch)
        if len(pending) >= 2000:
            count += persist_batch(repository, pending)
            pending = []
    count += persist_batch(repository, pending)
    logger.info("Histórico simulado gerado: %d leituras.", count)
    return count

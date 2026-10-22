from app.config import Settings
from app.data_sources.base import DataSource
from app.data_sources.simulator import SimulatorDataSource
from app.data_sources.tuya import TuyaDataSource
from app.services.equipment import list_equipment


def create_source(settings: Settings, *, engine=None) -> DataSource:
    if settings.data_source == "tuya":
        return TuyaDataSource(settings)
    provider = None if engine is None else lambda: list_equipment(engine)
    return SimulatorDataSource(seed=settings.simulation_seed, settings=settings, equipment_provider=provider)

"""Ponto de extensão futuro. Nenhuma conexão ou credencial real é utilizada."""

from datetime import datetime

from app.config import Settings
from app.data_sources.base import DataSource
from app.data_sources.readings import Reading


class TuyaDataSource(DataSource):
    def __init__(self, settings: Settings):
        self.settings = settings

    def get_current_readings(self, timestamp: datetime | None = None) -> list[Reading]:
        raise NotImplementedError(
            "Integração Tuya futura. Use DATA_SOURCE=simulator nesta versão."
        )

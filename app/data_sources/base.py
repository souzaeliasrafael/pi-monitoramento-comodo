"""O domínio depende deste contrato, nunca do SDK de um fabricante."""

from abc import ABC, abstractmethod
from datetime import datetime

from app.data_sources.readings import Reading


class DataSource(ABC):
    @abstractmethod
    def get_current_readings(self, timestamp: datetime | None = None) -> list[Reading]:
        """Entrega leituras normalizadas nas unidades e horário definidos em Reading."""
        raise NotImplementedError

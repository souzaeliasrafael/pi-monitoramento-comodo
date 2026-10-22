"""Consultas e escrita transacional, com unicidade por dispositivo/instante."""

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine

from app.data_sources.readings import Reading
from app.database.models import ReadingRecord


class Repository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def insert_readings(self, readings: list[Reading]) -> int:
        for reading in readings:
            reading.validate()
        if not readings:
            return 0
        statement = insert(ReadingRecord).on_conflict_do_nothing(index_elements=["timestamp", "device_id"])
        with self.engine.begin() as conn:
            result = conn.execute(statement, [asdict(row) for row in readings])
            return result.rowcount

    def query(self, start: datetime | None = None, end: datetime | None = None,
              device_id: str | None = None) -> list[dict]:
        """Período fechado nas duas extremidades; serviços definem seus próprios bins."""
        stmt = select(ReadingRecord)
        if start is not None:
            stmt = stmt.where(ReadingRecord.timestamp >= start)
        if end is not None:
            stmt = stmt.where(ReadingRecord.timestamp <= end)
        if device_id is not None:
            stmt = stmt.where(ReadingRecord.device_id == device_id)
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(stmt.order_by(ReadingRecord.timestamp, ReadingRecord.device_id)).mappings()]

    def latest(self, device_id: str) -> dict | None:
        stmt = select(ReadingRecord).where(ReadingRecord.device_id == device_id).order_by(ReadingRecord.timestamp.desc()).limit(1)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row is not None else None

    def summary(self) -> list[dict]:
        stmt = select(ReadingRecord.device_id, func.count().label("count"),
                      func.avg(ReadingRecord.temperature_c).label("temperature_mean"),
                      func.avg(ReadingRecord.power_w).label("power_mean"))
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(stmt.group_by(ReadingRecord.device_id)).mappings()]

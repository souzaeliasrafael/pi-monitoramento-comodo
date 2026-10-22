"""Modelos persistentes de leituras normalizadas e alertas agrupados."""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, Float, String, UniqueConstraint
from datetime import datetime


class Base(DeclarativeBase):
    pass


class EquipmentRecord(Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    quantity: Mapped[int]
    power_w: Mapped[float] = mapped_column(Float)
    start_hour: Mapped[float] = mapped_column(Float)
    duration_hours: Mapped[float] = mapped_column(Float)
    active_from: Mapped[datetime] = mapped_column(DateTime)


class ForecastRecord(Base):
    __tablename__ = "forecasts"
    __table_args__ = (UniqueConstraint("issued_at", "target"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    training_end: Mapped[datetime] = mapped_column(DateTime)
    target: Mapped[datetime] = mapped_column(DateTime, index=True)
    prediction: Mapped[float] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    actual: Mapped[float | None] = mapped_column(Float)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime)
    origin: Mapped[str] = mapped_column(String(30))


class ReadingRecord(Base):
    __tablename__ = "readings"
    __table_args__ = (UniqueConstraint("timestamp", "device_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    device_id: Mapped[str] = mapped_column(String(100), index=True)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_percent: Mapped[float | None] = mapped_column(Float)
    voltage_v: Mapped[float | None] = mapped_column(Float)
    current_a: Mapped[float | None] = mapped_column(Float)
    power_w: Mapped[float | None] = mapped_column(Float)
    energy_kwh: Mapped[float | None] = mapped_column(Float)


class AlertRecord(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("timestamp", "device_id", "type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    device_id: Mapped[str] = mapped_column(String(100), index=True)
    type: Mapped[str] = mapped_column(String(40))
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(300))
    observed: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)


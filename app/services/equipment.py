"""Equipamentos adicionais e integração do uso dinâmico do circuito."""
import math

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import local_now
from app.database.models import EquipmentRecord
from app.services.dynamic_usage import dynamic_load


def list_equipment(engine):
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(select(EquipmentRecord.__table__).order_by(EquipmentRecord.id)).mappings()]


def add_equipment(engine, name, quantity, power_w, *, active_from=None):
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("Informe um nome com até 100 caracteres.")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1000:
        raise ValueError("Informe uma quantidade inteira entre 1 e 1.000.")
    if not math.isfinite(power_w) or not 0 < power_w <= 100000:
        raise ValueError("Informe uma potência positiva e até 100.000 W.")
    active_from = active_from or local_now()
    if active_from.tzinfo is not None:
        raise ValueError("Use horário local de Brasília sem offset.")
    try:
        with engine.begin() as connection:
            connection.execute(EquipmentRecord.__table__.insert().values(name=name, quantity=quantity,
                power_w=power_w, start_hour=0, duration_hours=0, active_from=active_from))
    except IntegrityError:
        raise ValueError("Já existe um equipamento com esse nome. Use um nome diferente.") from None


def equipment_load(equipment, start, end, *, seed=42, minimum=8.0, maximum=10.0):
    """Retorna potência no instante final e kWh no intervalo, sem retroagir cadastro."""
    watts, energy = 0.0, 0.0
    for item in equipment:
        if end < item["active_from"]:
            continue
        begin = max(start, item["active_from"])
        # Colunas antigas de programação são mantidas apenas para ler bancos antigos.
        power, used = dynamic_load(begin, end, item["quantity"], item["power_w"], seed,
                                  group=item["name"], minimum=minimum, maximum=maximum)
        watts += power
        energy += used
    return watts, energy

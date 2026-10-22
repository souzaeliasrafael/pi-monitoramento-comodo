"""Carga de iluminação variável observada pelo disjuntor inteligente."""
from app.services.dynamic_usage import dynamic_load


def lighting_power(timestamp, settings):
    return dynamic_load(timestamp, timestamp, settings.lamp_count, settings.lamp_power_w,
                        settings.simulation_seed, minimum=settings.usage_hours_min,
                        maximum=settings.usage_hours_max)[0]


def lighting_energy(start, end, settings):
    return dynamic_load(start, end, settings.lamp_count, settings.lamp_power_w,
                        settings.simulation_seed, minimum=settings.usage_hours_min,
                        maximum=settings.usage_hours_max)[1]

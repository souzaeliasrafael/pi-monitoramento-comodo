"""Ocupação sintética variável; horas de atividade são a união das sessões."""
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import random


@lru_cache(maxsize=8192)
def daily_sessions(day, seed=42, minimum=8.0, maximum=10.0):
    if day.weekday() == 6:
        return ()
    rng = random.Random(f"occupancy:{seed}:{day.isoformat()}")
    fraction = .65 * rng.random() + (.35 if day.weekday() >= 5 else .05)
    if day >= datetime(2026, 9, 24):
        fraction += .12
    hours = minimum + (maximum - minimum) * min(1, fraction)
    first, last = rng.uniform(5.5, 8.0), rng.uniform(22.0, 23.9)
    weights = [rng.uniform(.6, 1.5) for _ in range(6)]
    durations = [weight / sum(weights) * hours for weight in weights]
    breaks = [rng.uniform(.3, 1.4) for _ in range(5)]
    gaps = [weight / sum(breaks) * (last - first - hours) for weight in breaks]
    sessions, cursor = [], first
    for i, duration in enumerate(durations):
        sessions.append((day + timedelta(hours=cursor), day + timedelta(hours=cursor + duration)))
        cursor += duration + (gaps[i] if i < len(gaps) else 0)
    if day.weekday() == 5:
        noon = day + timedelta(hours=12)
        sessions = [(on, min(off, noon)) for on, off in sessions if on < noon]
    return tuple(sessions)


@lru_cache(maxsize=16384)
def daily_load(day, quantity, nominal_w, seed=42, group="lighting", minimum=8.0, maximum=10.0):
    rng = random.Random(hashlib.sha256(f"{seed}:{day.isoformat()}:{group}".encode()).digest())
    segments = []
    for on, off in daily_sessions(day, seed, minimum, maximum):
        cursor = on
        while cursor < off:
            boundary = min(off, cursor + timedelta(minutes=rng.uniform(15, 50)))
            active = max(1, sum(rng.random() < .76 for _ in range(quantity)))
            power = active * nominal_w * rng.uniform(.97, 1.0)
            segments.append((cursor, boundary, power))
            cursor = boundary
    return tuple(segments)


def dynamic_load(start, end, quantity, nominal_w, seed=42, group="lighting", minimum=8.0, maximum=10.0):
    """Potência no instante final e integral exata em kWh entre amostras."""
    if end < start:
        raise ValueError("Intervalo de consumo fora de ordem.")
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    power, energy = 0.0, 0.0
    while day <= end:
        for on, off, watts in daily_load(day, quantity, nominal_w, seed, group, minimum, maximum):
            if on <= end < off:
                power = watts
            seconds = max(0, (min(end, off) - max(start, on)).total_seconds())
            energy += watts * seconds / 3600000
        day += timedelta(days=1)
    return power, energy

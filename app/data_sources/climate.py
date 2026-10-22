"""Médias climatológicas de Mauá/SP; não são observações de 2026.

Fonte: https://www.climatempo.com.br/climatologia/488/maua-sp
Consulta em 04/10/2026. Pares: mínima média e máxima média, em °C.
"""

from datetime import datetime

MONTHLY_TEMPERATURES = (
    (20, 27), (20, 27), (19, 26), (17, 24), (15, 22), (13, 21),
    (13, 21), (13, 22), (15, 23), (16, 24), (17, 24), (19, 26),
)


def temperature_reference(timestamp: datetime) -> tuple[float, float]:
    """Interpola entre os centros dos meses para evitar saltos na mudança de mês."""
    current = datetime(timestamp.year, timestamp.month, 15)
    if timestamp < current:
        previous_month = 12 if timestamp.month == 1 else timestamp.month - 1
        left = datetime(timestamp.year - (timestamp.month == 1), previous_month, 15)
        right = current
    else:
        next_month = 1 if timestamp.month == 12 else timestamp.month + 1
        left = current
        right = datetime(timestamp.year + (timestamp.month == 12), next_month, 15)
    fraction = (timestamp - left).total_seconds() / (right - left).total_seconds()
    low_a, high_a = MONTHLY_TEMPERATURES[left.month - 1]
    low_b, high_b = MONTHLY_TEMPERATURES[right.month - 1]
    return low_a + fraction * (low_b - low_a), high_a + fraction * (high_b - high_a)

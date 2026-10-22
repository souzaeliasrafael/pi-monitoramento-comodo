"""Consumo e custo simples, sem impostos ou bandeiras tarifárias."""

import math
import pandas as pd

from app.services.analytics import consumption_by_period


def with_cost(periods: pd.DataFrame, price: float) -> pd.DataFrame:
    if not math.isfinite(price) or price < 0:
        raise ValueError("Tarifa deve ser finita e não negativa.")
    result = periods.copy()
    result["cost_brl"] = result.consumption_kwh * price
    return result


def energy_summary(frame: pd.DataFrame, price: float, now=None) -> dict:
    daily = with_cost(consumption_by_period(frame), price)
    day = pd.Timestamp(now if now is not None else pd.Timestamp.now()).normalize()
    today = daily[daily.timestamp == day]
    week = daily[(daily.timestamp >= day - pd.Timedelta(days=6)) & (daily.timestamp <= day)]
    complete = daily[(daily.timestamp < day) & (daily.timestamp >= day - pd.Timedelta(days=7)) & (daily.coverage_hours >= 23.999)]
    recent = complete.tail(7)
    monthly = None if recent.empty else float(recent.consumption_kwh.mean() * day.days_in_month * price)
    return {"total_kwh": float(daily.consumption_kwh.sum()),
            "today_kwh": float(today.consumption_kwh.sum()),
            "today_cost": float(today.cost_brl.sum()),
            "week_kwh": float(week.consumption_kwh.sum()),
            "week_cost": float(week.cost_brl.sum()),
            "estimated_month_cost": monthly,
            "today_coverage_hours": float(today.coverage_hours.sum()),
            "excluded_intervals": daily.attrs.get("excluded_intervals", 0)}

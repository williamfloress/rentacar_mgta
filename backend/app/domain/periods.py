"""Cálculo de periodos mensuales para las métricas (lógica pura)."""

from datetime import date


def month_start(day: date) -> date:
    return day.replace(day=1)


def add_months(first_of_month: date, months: int) -> date:
    """Suma (o resta) meses a una fecha que es día 1. Ej.: 2026-11-01 + 2 → 2027-01-01."""
    index = first_of_month.year * 12 + (first_of_month.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def last_month_starts(today: date, count: int) -> list[date]:
    """Los `count` meses que terminan en el mes actual, del más antiguo al más reciente."""
    current = month_start(today)
    return [add_months(current, -offset) for offset in range(count - 1, -1, -1)]

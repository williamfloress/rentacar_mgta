"""Reglas de precio del alquiler.

Este módulo es lógica PURA: no importa FastAPI, ni SQLAlchemy, ni la base de
datos. Recibe valores y devuelve valores. Eso lo hace trivial de probar
(ver tests/test_pricing.py) y fácil de explicar en una entrevista: "las reglas
de negocio no dependen del framework".

Dinero: se usa Decimal, NUNCA float (0.1 + 0.2 != 0.3 con float; en facturación
eso se convierte en céntimos que no cuadran).
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Redondea a 2 decimales (mitad hacia arriba, como en contabilidad)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def rental_days(start: date, end: date) -> int:
    """Número de días cobrados.

    El rango es semiabierto [inicio, fin): del 10 al 15 son 5 días y el día 15
    (devolución) no se cobra. Debe coincidir con el rango que usa la restricción
    anti-solapamiento de la base de datos.
    """
    days = (end - start).days
    if days <= 0:
        raise ValueError("end date must be after start date")
    return days


def calculate_total(daily_rate: Decimal, start: date, end: date) -> Decimal:
    """Total base del alquiler = tarifa diaria × días."""
    return money(daily_rate * rental_days(start, end))


def calculate_late_fee(
    daily_rate: Decimal,
    end_date: date,
    returned_on: date,
    multiplier: Decimal,
) -> Decimal:
    """Recargo por devolución tardía.

    Cada día de retraso se cobra `tarifa × multiplier` (p. ej. 1.5 = un 50 %
    más caro que un día normal). Devolver a tiempo o antes no genera recargo.
    El multiplicador es una SUPOSICIÓN de negocio configurable (LATE_FEE_MULTIPLIER);
    cada agencia podría querer otra política.
    """
    late_days = (returned_on - end_date).days
    if late_days <= 0:
        return Decimal("0.00")
    return money(daily_rate * multiplier * late_days)

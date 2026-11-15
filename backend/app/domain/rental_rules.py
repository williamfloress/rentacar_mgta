"""Ciclo de vida de un alquiler (máquina de estados) y validación de fechas.

Lógica pura, igual que pricing.py.

    reserved ──► active ──► returned
        │
        └──────► cancelled

* reserved : reservado, aún no ha salido el vehículo.
* active   : el cliente tiene el vehículo.
* returned : devuelto (estado final).
* cancelled: cancelado antes de entregar (estado final).

Por qué una máquina de estados explícita: evita estados absurdos (devolver un
alquiler cancelado, reactivar uno devuelto) y concentra la regla en UN sitio en
vez de repartir `if`s por los endpoints.
"""

from datetime import date
from enum import StrEnum


class RentalStatus(StrEnum):
    RESERVED = "reserved"
    ACTIVE = "active"
    RETURNED = "returned"
    CANCELLED = "cancelled"


# Estados que OCUPAN el vehículo. Deben coincidir con la cláusula WHERE de la
# restricción rentals_no_overlap en la base de datos.
BLOCKING_STATUSES = (RentalStatus.RESERVED, RentalStatus.ACTIVE)

ALLOWED_TRANSITIONS: dict[RentalStatus, frozenset[RentalStatus]] = {
    RentalStatus.RESERVED: frozenset({RentalStatus.ACTIVE, RentalStatus.CANCELLED}),
    RentalStatus.ACTIVE: frozenset({RentalStatus.RETURNED}),
    RentalStatus.RETURNED: frozenset(),
    RentalStatus.CANCELLED: frozenset(),
}


class InvalidTransition(Exception):
    """Se intentó un cambio de estado que el ciclo de vida no permite."""


def ensure_transition(current: RentalStatus, target: RentalStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(f"cannot change a rental from '{current.value}' to '{target.value}'")


def ensure_can_start(start_date: date, today: date) -> None:
    """Un vehículo no puede entregarse ANTES de la fecha reservada.

    Si se entregara antes, el cliente lo tendría en días que el rango de la
    reserva no cubre, y otra reserva podría ocupar esos mismos días: la garantía
    anti-solapamiento de la base de datos dejaría de reflejar la realidad.
    """
    if today < start_date:
        raise InvalidTransition(f"rental cannot start before its start_date ({start_date.isoformat()})")


def validate_new_rental_dates(start: date, end: date, today: date) -> None:
    """Valida las fechas de un alquiler NUEVO. Lanza ValueError si no son válidas."""
    if end <= start:
        raise ValueError("end_date must be after start_date")
    if start < today:
        raise ValueError("start_date cannot be in the past")

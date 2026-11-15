"""¿Está ocupado un vehículo en un rango de fechas? Una sola definición para toda la API.

Un vehículo está ocupado en [start, end) si tiene un alquiler que:
  1. está 'reserved' o 'active' y su rango se cruza con el pedido
     (dos rangos semiabiertos [a, b) y [c, d) se cruzan cuando a < d y c < b), o
  2. está 'active' con la devolución VENCIDA (end_date < hoy): el cliente aún
     tiene el carro, así que sigue fuera aunque su rango pactado ya terminó.
     No se sabe cuándo volverá, por eso bloquea cualquier fecha desde su inicio.

El caso 1 lo garantiza además la restricción EXCLUDE de PostgreSQL. El caso 2
depende de "hoy" y no se puede expresar en una restricción: lo comprueba la
aplicación (ver create_rental en routers/rentals.py). Es una comprobación previa con una ventana de
carrera teórica, aceptable porque el caso es raro y no produce dobles reservas
en el rango pactado; queda documentado en docs/04-roadmap.md.
"""

import uuid
from datetime import date

from sqlalchemy import Exists, and_, or_, select

from app.domain.rental_rules import BLOCKING_STATUSES, RentalStatus
from app.models import Rental, Vehicle


def vehicle_busy(tenant_id: uuid.UUID, start: date, end: date, today: date) -> Exists:
    """Subconsulta EXISTS correlacionada con `Vehicle.id`, para usar en un WHERE."""
    return (
        select(Rental.id)
        .where(
            Rental.vehicle_id == Vehicle.id,
            Rental.tenant_id == tenant_id,
            or_(
                and_(
                    Rental.status.in_([s.value for s in BLOCKING_STATUSES]),
                    Rental.start_date < end,
                    Rental.end_date > start,
                ),
                and_(
                    Rental.status == RentalStatus.ACTIVE.value,
                    Rental.end_date < today,
                    Rental.start_date < end,
                ),
            ),
        )
        .exists()
    )

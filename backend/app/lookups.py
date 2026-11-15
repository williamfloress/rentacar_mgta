"""Búsquedas por id con filtro de agencia explícito.

Cada consulta añade `tenant_id == user.tenant_id` A MANO, aunque RLS ya filtre
en la base de datos. Son dos candados independientes ("defensa en
profundidad"): si algún día la app se conectara por error con un rol que se
salta RLS (en Neon/Supabase es fácil), este filtro sigue protegiendo los datos.

Se devuelve 404 (no 403) cuando el recurso es de otra agencia: así no se revela
ni siquiera que ese id existe.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Customer, Rental, User, Vehicle


def _not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


def get_vehicle_or_404(db: Session, user: User, vehicle_id: uuid.UUID) -> Vehicle:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.tenant_id == user.tenant_id))
    if vehicle is None:
        raise _not_found("Vehicle")
    return vehicle


def get_customer_or_404(db: Session, user: User, customer_id: uuid.UUID) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.tenant_id == user.tenant_id))
    if customer is None:
        raise _not_found("Customer")
    return customer


def get_rental_or_404(db: Session, user: User, rental_id: uuid.UUID) -> Rental:
    rental = db.scalar(
        select(Rental)
        .options(joinedload(Rental.vehicle), joinedload(Rental.customer))
        .where(Rental.id == rental_id, Rental.tenant_id == user.tenant_id)
    )
    if rental is None:
        raise _not_found("Rental")
    return rental

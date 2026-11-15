"""Vehículos: CRUD y búsqueda de disponibilidad por fechas."""

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app import audit
from app.availability import vehicle_busy
from app.clock import today
from app.deps import CurrentUser, DbSession, OwnerUser
from app.domain.rental_rules import BLOCKING_STATUSES
from app.errors import FOREIGN_KEY_VIOLATION, UNIQUE_VIOLATION, pg_code
from app.lookups import get_vehicle_or_404
from app.models import Rental, Vehicle
from app.pagination import PageParams
from app.schemas import VehicleCreate, VehicleOut, VehicleStatus, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
def list_vehicles(
    db: DbSession,
    user: CurrentUser,
    page: PageParams,
    response: Response,
    status_filter: VehicleStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=60, description="Busca en placa, marca o modelo"),
) -> list[Vehicle]:
    stmt = select(Vehicle).where(Vehicle.tenant_id == user.tenant_id)
    if status_filter:
        stmt = stmt.where(Vehicle.status == status_filter)
    if q:
        # autoescape=True neutraliza los comodines (% y _) que escriba el usuario.
        stmt = stmt.where(
            or_(
                Vehicle.plate.icontains(q, autoescape=True),
                Vehicle.brand.icontains(q, autoescape=True),
                Vehicle.model.icontains(q, autoescape=True),
            )
        )
    return list(db.scalars(page.apply(db, stmt, response).order_by(Vehicle.plate)))


# IMPORTANTE: esta ruta va ANTES de "/{vehicle_id}"; si no, FastAPI intentaría
# interpretar la palabra "available" como un UUID y respondería 422.
@router.get("/available", response_model=list[VehicleOut])
def available_vehicles(
    db: DbSession,
    user: CurrentUser,
    start_date: date,
    end_date: date,
) -> list[Vehicle]:
    """Vehículos libres para TODO el rango [start_date, end_date).

    Un vehículo está libre si está 'active' y no tiene ningún alquiler
    'reserved'/'active' cuyo rango se cruce con el pedido. Dos rangos
    semiabiertos [a, b) y [c, d) se cruzan cuando  a < d  y  c < b.
    """
    if end_date <= start_date:
        raise HTTPException(422, detail="end_date must be after start_date")

    busy = vehicle_busy(user.tenant_id, start_date, end_date, today())
    stmt = (
        select(Vehicle)
        .where(Vehicle.tenant_id == user.tenant_id, Vehicle.status == "active", ~busy)
        .order_by(Vehicle.plate)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(body: VehicleCreate, db: DbSession, user: CurrentUser) -> Vehicle:
    vehicle = Vehicle(tenant_id=user.tenant_id, **body.model_dump())
    try:
        db.add(vehicle)
        db.flush()
        audit.record(db, user, "vehicle.created", "vehicle", vehicle.id, {"plate": vehicle.plate})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == UNIQUE_VIOLATION:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="A vehicle with that plate already exists") from None
        raise
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Vehicle:
    return get_vehicle_or_404(db, user, vehicle_id)


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(vehicle_id: uuid.UUID, body: VehicleUpdate, db: DbSession, user: CurrentUser) -> Vehicle:
    vehicle = get_vehicle_or_404(db, user, vehicle_id)
    changes = body.model_dump(exclude_unset=True)  # solo los campos que el cliente envió
    new_status = changes.get("status")
    if new_status in {"maintenance", "retired"} and new_status != vehicle.status:
        _ensure_no_upcoming_bookings(db, vehicle)
    for field, value in changes.items():
        if value is None and field in {"plate", "brand", "model", "year", "daily_rate", "status"}:
            continue  # estos campos son obligatorios: un null explícito se ignora
        setattr(vehicle, field, value)
    try:
        audit.record(db, user, "vehicle.updated", "vehicle", vehicle.id, {"fields": sorted(changes)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == UNIQUE_VIOLATION:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="A vehicle with that plate already exists") from None
        raise
    return vehicle


def _ensure_no_upcoming_bookings(db, vehicle: Vehicle) -> None:
    """Un vehículo con reservas pendientes o en curso no puede pasar a taller ni darse de baja.

    Si se permitiera, esas reservas quedarían prometidas sobre un carro que no
    va a estar disponible. La agencia debe primero cancelarlas o terminarlas.
    """
    pending = (
        db.scalar(
            select(func.count())
            .select_from(Rental)
            .where(
                Rental.tenant_id == vehicle.tenant_id,
                Rental.vehicle_id == vehicle.id,
                Rental.status.in_([s.value for s in BLOCKING_STATUSES]),
                Rental.end_date > today(),
            )
        )
        or 0
    )
    if pending:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Vehicle has {pending} pending or ongoing rental(s); resolve them first",
        )


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: uuid.UUID, db: DbSession, user: OwnerUser) -> Response:
    """Solo el dueño. Si el vehículo ya tiene historial de alquileres no se puede
    borrar (la clave foránea lo impide): hay que marcarlo como 'retired'."""
    vehicle = get_vehicle_or_404(db, user, vehicle_id)
    try:
        audit.record(db, user, "vehicle.deleted", "vehicle", vehicle.id, {"plate": vehicle.plate})
        db.delete(vehicle)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == FOREIGN_KEY_VIOLATION:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Vehicle has rental history; set its status to 'retired' instead",
            ) from None
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)

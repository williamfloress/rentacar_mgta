"""Alquileres: creación con control de solapamiento, listado y cambios de estado."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app import audit
from app.clock import today
from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.domain.pricing import calculate_late_fee, calculate_total
from app.domain.rental_rules import (
    InvalidTransition,
    RentalStatus,
    ensure_can_start,
    ensure_transition,
    validate_new_rental_dates,
)
from app.errors import EXCLUSION_VIOLATION, FOREIGN_KEY_VIOLATION, pg_code
from app.lookups import get_customer_or_404, get_rental_or_404, get_vehicle_or_404
from app.models import Customer, Rental, Vehicle
from app.pagination import PageParams
from app.schemas import RentalCreate, RentalOut, RentalStatusChange

router = APIRouter(prefix="/rentals", tags=["rentals"])


@router.get("", response_model=list[RentalOut])
def list_rentals(
    db: DbSession,
    user: CurrentUser,
    status_filter: RentalStatus | None = Query(default=None, alias="status"),
    vehicle_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=60, description="Busca por placa o nombre/documento del cliente"),
    *,
    page: PageParams,
    response: Response,
) -> list[Rental]:
    stmt = select(Rental).where(Rental.tenant_id == user.tenant_id)
    if status_filter:
        stmt = stmt.where(Rental.status == status_filter.value)
    if vehicle_id:
        stmt = stmt.where(Rental.vehicle_id == vehicle_id)
    if customer_id:
        stmt = stmt.where(Rental.customer_id == customer_id)
    if q:
        stmt = stmt.where(
            or_(
                Rental.vehicle.has(Vehicle.plate.icontains(q, autoescape=True)),
                Rental.customer.has(Customer.full_name.icontains(q, autoescape=True)),
                Rental.customer.has(Customer.document_id.icontains(q, autoescape=True)),
            )
        )
    # Las opciones de carga (joinedload) se añaden DESPUÉS de contar: el conteo
    # no necesita traer vehículo ni cliente.
    stmt = (
        page.apply(db, stmt, response)
        .options(joinedload(Rental.vehicle), joinedload(Rental.customer))
        .order_by(Rental.start_date.desc(), Rental.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.post("", response_model=RentalOut, status_code=status.HTTP_201_CREATED)
def create_rental(body: RentalCreate, db: DbSession, user: CurrentUser) -> Rental:
    """Crea una reserva.

    NOTA DE DISEÑO: aquí NO se consulta "¿está libre el vehículo?" antes de
    insertar. Esa comprobación previa tendría una condición de carrera: dos
    peticiones simultáneas podrían ver "libre" a la vez y reservar ambas. En
    su lugar se INTENTA insertar y la restricción EXCLUDE de PostgreSQL
    rechaza la segunda de forma atómica; nosotros solo traducimos el error.
    """
    try:
        validate_new_rental_dates(body.start_date, body.end_date, today())
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None

    vehicle = get_vehicle_or_404(db, user, body.vehicle_id)
    customer = get_customer_or_404(db, user, body.customer_id)
    # La reserva solapada la rechaza PostgreSQL al insertar; lo que la BD no puede
    # saber es si el carro sigue fuera con la devolución vencida (ver availability.py).
    still_out = db.scalar(
        select(Rental.id)
        .where(
            Rental.tenant_id == user.tenant_id,
            Rental.vehicle_id == vehicle.id,
            Rental.status == RentalStatus.ACTIVE.value,
            Rental.end_date < today(),
            Rental.start_date < body.end_date,
        )
        .limit(1)
    )
    if still_out:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Vehicle is still out with an overdue return")
    if vehicle.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Vehicle is not available for rental ({vehicle.status})")

    rental = Rental(
        tenant_id=user.tenant_id,
        vehicle_id=vehicle.id,
        customer_id=customer.id,
        start_date=body.start_date,
        end_date=body.end_date,
        # Se "congela" la tarifa de hoy: cambios futuros de precio no alteran este alquiler.
        daily_rate_snapshot=vehicle.daily_rate,
        total_amount=calculate_total(vehicle.daily_rate, body.start_date, body.end_date),
        status=RentalStatus.RESERVED.value,
        notes=body.notes,
        created_by=user.id,
    )
    try:
        db.add(rental)
        db.flush()
        audit.record(
            db,
            user,
            "rental.created",
            "rental",
            rental.id,
            {"vehicle_id": str(vehicle.id), "customer_id": str(customer.id)},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        code = pg_code(exc)
        if code == EXCLUSION_VIOLATION:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Vehicle is already booked in that period") from None
        if code == FOREIGN_KEY_VIOLATION:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Vehicle or customer no longer exists") from None
        raise
    return get_rental_or_404(db, user, rental.id)  # se recarga con vehículo y cliente incluidos


@router.get("/{rental_id}", response_model=RentalOut)
def get_rental(rental_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Rental:
    return get_rental_or_404(db, user, rental_id)


@router.post("/{rental_id}/status", response_model=RentalOut)
def change_rental_status(rental_id: uuid.UUID, body: RentalStatusChange, db: DbSession, user: CurrentUser) -> Rental:
    """Avanza el ciclo de vida: reserved → active → returned, o reserved → cancelled."""
    rental = get_rental_or_404(db, user, rental_id)
    current = RentalStatus(rental.status)
    try:
        ensure_transition(current, body.status)
        if body.status is RentalStatus.ACTIVE:
            ensure_can_start(rental.start_date, today())
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None

    if body.status is RentalStatus.RETURNED:
        # Al devolver se calcula el recargo, si hubo retraso respecto a la fecha pactada.
        rental.returned_at = datetime.now(UTC)
        rental.late_fee = calculate_late_fee(
            rental.daily_rate_snapshot,
            rental.end_date,
            today(),
            get_settings().late_fee_multiplier,
        )
    rental.status = body.status.value
    audit.record(
        db,
        user,
        "rental.status_changed",
        "rental",
        rental.id,
        {"from": current.value, "to": body.status.value},
    )
    db.commit()
    return rental

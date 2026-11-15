"""Métricas y agenda para el panel principal."""

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.availability import vehicle_busy
from app.clock import today
from app.deps import CurrentUser, DbSession
from app.domain.periods import add_months, last_month_starts, month_start
from app.domain.pricing import money
from app.domain.rental_rules import RentalStatus
from app.models import Rental, Vehicle
from app.schemas import AgendaOut, DashboardOut, MonthlyRevenueOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Alquileres que cuentan como ingreso: el vehículo salió (está fuera o ya volvió).
_REVENUE_STATUSES = [RentalStatus.ACTIVE.value, RentalStatus.RETURNED.value]


@router.get("/summary", response_model=DashboardOut)
def summary(db: DbSession, user: CurrentUser) -> DashboardOut:
    tenant = user.tenant_id
    now = today()
    this_month = month_start(now)

    def count_rentals(*conditions) -> int:
        return db.scalar(select(func.count()).select_from(Rental).where(Rental.tenant_id == tenant, *conditions)) or 0

    vehicles_total = (
        db.scalar(
            select(func.count()).select_from(Vehicle).where(Vehicle.tenant_id == tenant, Vehicle.status != "retired")
        )
        or 0
    )

    # Vehículos libres HOY: activos y sin alquiler que los ocupe hoy (incluye devoluciones vencidas).
    occupied_today = vehicle_busy(tenant, now, now + timedelta(days=1), now)
    available_today = (
        db.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.tenant_id == tenant, Vehicle.status == "active", ~occupied_today)
        )
        or 0
    )

    revenue = db.scalar(
        select(func.coalesce(func.sum(Rental.total_amount + Rental.late_fee), 0)).where(
            Rental.tenant_id == tenant,
            Rental.status.in_(_REVENUE_STATUSES),
            Rental.start_date >= this_month,
            Rental.start_date < add_months(this_month, 1),
        )
    )

    return DashboardOut(
        vehicles_total=vehicles_total,
        vehicles_available_today=available_today,
        rentals_active=count_rentals(Rental.status == RentalStatus.ACTIVE.value),
        rentals_reserved=count_rentals(Rental.status == RentalStatus.RESERVED.value),
        # En curso y con la fecha de devolución ya pasada: hay que llamar al cliente.
        rentals_overdue=count_rentals(Rental.status == RentalStatus.ACTIVE.value, Rental.end_date < now),
        revenue_current_month=money(Decimal(revenue or 0)),
    )


@router.get("/agenda", response_model=AgendaOut)
def agenda(
    db: DbSession,
    user: CurrentUser,
    days: int = Query(default=7, ge=1, le=31, description="Horizonte de entregas próximas"),
) -> AgendaOut:
    """Lo que el mostrador tiene que atender: entregas próximas y devoluciones pendientes."""
    now = today()
    base = (
        select(Rental)
        .options(joinedload(Rental.vehicle), joinedload(Rental.customer))
        .where(Rental.tenant_id == user.tenant_id)
    )
    pickups = db.scalars(
        base.where(
            Rental.status == RentalStatus.RESERVED.value,
            Rental.start_date <= now + timedelta(days=days),
        )
        .order_by(Rental.start_date)
        .limit(10)
    )
    # Las atrasadas salen primero porque su end_date es la más antigua.
    returns = db.scalars(base.where(Rental.status == RentalStatus.ACTIVE.value).order_by(Rental.end_date).limit(10))
    return AgendaOut(today=now, pickups=list(pickups), returns=list(returns))


@router.get("/revenue", response_model=list[MonthlyRevenueOut])
def revenue_by_month(
    db: DbSession,
    user: CurrentUser,
    months: int = Query(default=6, ge=1, le=24),
) -> list[MonthlyRevenueOut]:
    """Ingresos (total + recargos) por mes de inicio del alquiler; los meses sin ingresos valen 0."""
    periods = last_month_starts(today(), months)
    month = func.date_trunc("month", Rental.start_date).label("month")
    rows = db.execute(
        select(month, func.sum(Rental.total_amount + Rental.late_fee), func.count())
        .where(
            Rental.tenant_id == user.tenant_id,
            Rental.status.in_(_REVENUE_STATUSES),
            Rental.start_date >= periods[0],
            Rental.start_date < add_months(periods[-1], 1),
        )
        .group_by(month)
    ).all()
    by_month = {row[0].date(): (row[1], row[2]) for row in rows}
    return [
        MonthlyRevenueOut(
            month=start,
            revenue=money(Decimal(by_month.get(start, (0, 0))[0])),
            rentals=by_month.get(start, (0, 0))[1],
        )
        for start in periods
    ]

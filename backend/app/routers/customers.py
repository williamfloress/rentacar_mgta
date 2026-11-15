"""Clientes: CRUD y búsqueda por nombre o documento."""

import uuid

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app import audit
from app.deps import CurrentUser, DbSession, OwnerUser
from app.errors import FOREIGN_KEY_VIOLATION, UNIQUE_VIOLATION, pg_code
from app.lookups import get_customer_or_404
from app.models import Customer
from app.pagination import PageParams
from app.schemas import CustomerCreate, CustomerOut, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

_REQUIRED = {"document_id", "full_name"}


@router.get("", response_model=list[CustomerOut])
def list_customers(
    db: DbSession,
    user: CurrentUser,
    page: PageParams,
    response: Response,
    q: str | None = Query(default=None, max_length=60, description="Busca en nombre o documento"),
) -> list[Customer]:
    stmt = select(Customer).where(Customer.tenant_id == user.tenant_id)
    if q:
        # autoescape=True neutraliza los comodines (% y _) que escriba el usuario.
        stmt = stmt.where(
            or_(
                Customer.full_name.icontains(q, autoescape=True),
                Customer.document_id.icontains(q, autoescape=True),
            )
        )
    return list(db.scalars(page.apply(db, stmt, response).order_by(Customer.full_name)))


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, db: DbSession, user: CurrentUser) -> Customer:
    customer = Customer(tenant_id=user.tenant_id, **body.model_dump())
    try:
        db.add(customer)
        db.flush()
        audit.record(db, user, "customer.created", "customer", customer.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == UNIQUE_VIOLATION:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="A customer with that document already exists"
            ) from None
        raise
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Customer:
    return get_customer_or_404(db, user, customer_id)


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: uuid.UUID, body: CustomerUpdate, db: DbSession, user: CurrentUser) -> Customer:
    customer = get_customer_or_404(db, user, customer_id)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field in _REQUIRED:
            continue
        setattr(customer, field, value)
    try:
        audit.record(db, user, "customer.updated", "customer", customer.id, {"fields": sorted(changes)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == UNIQUE_VIOLATION:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="A customer with that document already exists"
            ) from None
        raise
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: uuid.UUID, db: DbSession, user: OwnerUser) -> Response:
    customer = get_customer_or_404(db, user, customer_id)
    try:
        audit.record(db, user, "customer.deleted", "customer", customer.id)
        db.delete(customer)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == FOREIGN_KEY_VIOLATION:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Customer has rental history and cannot be deleted"
            ) from None
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)

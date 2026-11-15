"""Esquemas Pydantic: lo que la API ACEPTA (…In/…Create/…Update) y DEVUELVE (…Out).

Separar "modelo de base de datos" de "esquema de la API" es una práctica clave:
así nunca se filtra por accidente un campo interno (p. ej. password_hash) y se
pueden validar las entradas antes de que toquen la base de datos.

Nota sobre dinero: Pydantic serializa Decimal como STRING en JSON ("40.00").
Es lo correcto para no perder precisión; el frontend debe tratarlo como texto
y formatearlo (o usar una librería decimal), no con parseFloat para calcular.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.rental_rules import RentalStatus

VehicleStatus = Literal["active", "maintenance", "retired"]
Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
MAX_YEAR = date.today().year + 1  # se admiten modelos del año siguiente


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    agency_name: str = Field(min_length=2, max_length=120)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    # Longitud mínima 10 (recomendación NIST: pesa más la longitud que las "reglas de complejidad")
    password: str = Field(min_length=10, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (tipo de token OAuth2, no es una contraseña)


class UserOut(ORMModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool


class MeOut(UserOut):
    """Perfil de la sesión: el usuario y los datos de su agencia que necesita el panel."""

    agency_name: str
    currency: str


class AgentCreate(BaseModel):
    """Alta de un empleado (rol 'agent') por parte del dueño de la agencia."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)


# ------------------------------------------------------------ vehicles
def _clean_plate(value: str | None) -> str | None:
    return value.strip().upper() if value is not None else value


class VehicleCreate(BaseModel):
    plate: str = Field(min_length=3, max_length=15)
    brand: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=60)
    color: str | None = Field(default=None, max_length=40)
    year: int = Field(ge=1950, le=MAX_YEAR)
    daily_rate: Money

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        return _clean_plate(value)


class VehicleUpdate(BaseModel):
    """Todos los campos son opcionales (PATCH): solo se cambia lo que se envía."""

    plate: str | None = Field(default=None, min_length=3, max_length=15)
    brand: str | None = Field(default=None, min_length=1, max_length=60)
    model: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = Field(default=None, max_length=40)
    year: int | None = Field(default=None, ge=1950, le=MAX_YEAR)
    daily_rate: Money | None = None
    status: VehicleStatus | None = None

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str | None) -> str | None:
        return _clean_plate(value)


class VehicleOut(ORMModel):
    id: UUID
    plate: str
    brand: str
    model: str
    color: str | None
    year: int
    daily_rate: Decimal
    status: VehicleStatus


# ----------------------------------------------------------- customers
class CustomerCreate(BaseModel):
    document_id: str = Field(min_length=3, max_length=30)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=200)

    @field_validator("document_id")
    @classmethod
    def _strip_document(cls, value: str) -> str:
        return value.strip()


class CustomerUpdate(BaseModel):
    document_id: str | None = Field(default=None, min_length=3, max_length=30)
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=200)


class CustomerOut(ORMModel):
    id: UUID
    document_id: str
    full_name: str
    phone: str | None
    email: str | None
    address: str | None


# -------------------------------------------------------------- rentals
class RentalCreate(BaseModel):
    vehicle_id: UUID
    customer_id: UUID
    start_date: date
    end_date: date
    notes: str | None = Field(default=None, max_length=500)


class RentalStatusChange(BaseModel):
    status: RentalStatus


class RentalOut(ORMModel):
    id: UUID
    start_date: date
    end_date: date
    daily_rate_snapshot: Decimal
    total_amount: Decimal
    late_fee: Decimal
    status: RentalStatus
    returned_at: datetime | None
    notes: str | None
    created_at: datetime
    vehicle: VehicleOut
    customer: CustomerOut


# ----------------------------------------------------------- dashboard
class DashboardOut(BaseModel):
    vehicles_total: int  # sin contar los dados de baja
    vehicles_available_today: int
    rentals_active: int
    rentals_reserved: int
    rentals_overdue: int  # en curso con la fecha de devolución ya vencida
    # Ingresos del mes en curso = total + recargos de los alquileres 'active' o
    # 'returned' cuya fecha de inicio cae en el mes. Es una DEFINICIÓN de
    # negocio documentada, no la única posible (p. ej. contable por devengo).
    revenue_current_month: Decimal


class AgendaOut(BaseModel):
    today: date
    pickups: list[RentalOut]  # reservas que salen pronto
    returns: list[RentalOut]  # alquileres en curso, los atrasados primero


class MonthlyRevenueOut(BaseModel):
    month: date  # primer día del mes
    revenue: Decimal
    rentals: int

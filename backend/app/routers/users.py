"""Gestión del personal de la agencia. Solo el DUEÑO puede usar estos endpoints.

Modelo de roles del MVP:
  * owner : crea la agencia al registrarse; puede borrar datos y gestionar personal.
  * agent : empleado; opera el día a día (flota, clientes, alquileres) pero no borra
            datos ni gestiona usuarios.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import audit
from app.deps import DbSession, OwnerUser
from app.errors import UNIQUE_VIOLATION, pg_code
from app.models import User
from app.schemas import AgentCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, owner: OwnerUser) -> list[User]:
    return list(db.scalars(select(User).where(User.tenant_id == owner.tenant_id).order_by(User.full_name)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_agent(body: AgentCreate, db: DbSession, owner: OwnerUser) -> User:
    agent = User(
        tenant_id=owner.tenant_id,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role="agent",  # el rol NO viene del cliente: un dueño solo puede crear agentes
    )
    try:
        db.add(agent)
        db.flush()
        audit.record(db, owner, "user.created", "user", agent.id, {"role": "agent"})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == UNIQUE_VIOLATION:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered") from None
        raise
    return agent


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: uuid.UUID, db: DbSession, owner: OwnerUser) -> User:
    """Desactiva una cuenta sin borrarla (se conserva el historial y la auditoría).

    El efecto es inmediato: get_current_user comprueba is_active en cada petición,
    así que el token que ese usuario ya tenga deja de funcionar al instante.
    """
    target = db.scalar(select(User).where(User.id == user_id, User.tenant_id == owner.tenant_id))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == owner.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="You cannot deactivate your own account")
    target.is_active = False
    audit.record(db, owner, "user.deactivated", "user", target.id)
    db.commit()
    return target

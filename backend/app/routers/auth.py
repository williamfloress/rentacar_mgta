"""Registro de agencia, login y perfil."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import audit
from app.deps import CurrentUser, DbSession
from app.errors import UNIQUE_VIOLATION, pg_code
from app.models import Tenant, User
from app.ratelimit import limit_auth_attempts
from app.schemas import MeOut, RegisterIn, TokenOut, UserOut
from app.security import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_auth_attempts)],
)
def register(body: RegisterIn, db: DbSession) -> TokenOut:
    """Crea una agencia nueva (tenant) y su primer usuario, que será el DUEÑO."""
    tenant_id = uuid.uuid4()
    # Generamos el id ANTES de insertar para poder fijar el contexto de agencia:
    # las políticas RLS exigen que la fila nueva pertenezca al tenant del contexto.
    db.info["tenant_id"] = str(tenant_id)

    tenant = Tenant(id=tenant_id, name=body.agency_name.strip())
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role="owner",
    )
    try:
        db.add(tenant)
        db.flush()  # la agencia debe existir antes que su usuario (clave foránea)
        db.add(user)
        db.flush()
        audit.record(db, user, "tenant.registered", "tenant", tenant_id)
        db.commit()  # agencia + usuario + auditoría: todo o nada
    except IntegrityError as exc:
        db.rollback()
        if pg_code(exc) == UNIQUE_VIOLATION:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered") from None
        raise
    return TokenOut(access_token=create_access_token(user.id, tenant_id))


@router.post("/login", response_model=TokenOut, dependencies=[Depends(limit_auth_attempts)])
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> TokenOut:
    """Inicio de sesión. Usa formulario estándar OAuth2 (el campo `username` es el email)."""
    email = form.username.strip().lower()
    # Aún no conocemos la agencia: declaramos el email buscado para que la
    # política RLS "login_lookup" deje ver únicamente esa fila de users.
    db.info["login_email"] = email
    user = db.scalar(select(User).where(User.email == email))

    # Se verifica SIEMPRE (con hash de relleno si no existe el usuario) para que
    # el tiempo de respuesta no delate qué emails están registrados.
    password_ok = verify_password(user.password_hash if user else DUMMY_HASH, form.password)
    if user is None or not password_ok or not user.is_active:
        # Mensaje genérico: no se distingue "no existe" de "contraseña incorrecta".
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=create_access_token(user.id, user.tenant_id))


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser, db: DbSession) -> MeOut:
    tenant = db.get(Tenant, user.tenant_id)  # RLS: solo puede ser la agencia del usuario
    return MeOut(
        **UserOut.model_validate(user).model_dump(),
        agency_name=tenant.name,
        currency=tenant.currency,
    )

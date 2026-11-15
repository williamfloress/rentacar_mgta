"""Dependencias de FastAPI: sesión de BD, usuario autenticado y control de roles.

Orden de una petición autenticada:
    token (cabecera Authorization: Bearer ...) → get_current_user:
        1. valida firma y caducidad del JWT
        2. fija el contexto de agencia en la sesión (para RLS, ver database.py)
        3. carga al usuario (RLS ya lo filtra por agencia) y comprueba que siga activo
    → el endpoint recibe un `User` ya verificado.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import User
from app.security import decode_access_token

# tokenUrl hace que Swagger (/docs) muestre el botón "Authorize" para probar la API.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[Session, Depends(get_session)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise unauthorized
    try:
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tid"])
    except ValueError:
        raise unauthorized from None

    db.info["tenant_id"] = str(tenant_id)  # a partir de aquí RLS filtra por esta agencia
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.tenant_id != tenant_id:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_owner(user: CurrentUser) -> User:
    """Solo el dueño de la agencia puede realizar la acción (p. ej. borrar datos)."""
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")
    return user


OwnerUser = Annotated[User, Depends(require_owner)]

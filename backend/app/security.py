"""Contraseñas y tokens.

* Contraseñas: Argon2id (ganador de la Password Hashing Competition y
  recomendación actual de OWASP). Nunca se guarda la contraseña, solo su hash
  con sal incorporada.
* Sesión: JWT firmado (HS256) de vida corta, con solo dos datos: quién es el
  usuario (sub) y de qué agencia (tid). El ROL no va en el token: se lee de la
  base de datos en cada petición, así un cambio de rol o una desactivación
  surten efecto al instante y no hay que esperar a que caduque el token.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings

_hasher = PasswordHasher()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


# Hash "de relleno": si el email no existe, igualmente verificamos contra este
# hash para que la respuesta tarde lo mismo que con un email real. Sin esto, un
# atacante podría descubrir qué emails están registrados midiendo tiempos.
DUMMY_HASH = _hasher.hash("not-a-real-password")


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Devuelve los datos del token, o None si es inválido o ha caducado."""
    try:
        return jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],  # lista explícita: evita ataques de "algoritmo none"
            options={"require": ["exp", "sub", "tid"]},
        )
    except jwt.PyJWTError:
        return None

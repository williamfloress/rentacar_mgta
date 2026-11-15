"""Configuración de la aplicación, leída de variables de entorno.

Principio: NINGÚN secreto vive en el código. En local se leen de un archivo
.env (ver .env.example, que sí se sube a git; .env no). En Render/Docker se
definen como variables de entorno del servicio.
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_KEY = "change-me-in-production"

_BACKEND_DIR = Path(__file__).resolve().parent.parent
# Archivos de entorno locales (si no existen se ignoran). El segundo tiene prioridad:
#   backend/.env       -> configuración local escrita a mano (ver .env.example)
#   <raíz>/.env.local  -> lo genera `neon init` con las conexiones del proyecto Neon
# Las variables de entorno reales (Docker, Render, CI) siempre ganan a ambos archivos.
_ENV_FILES = (_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env.local")


def _normalize_db_url(url: str) -> str:
    """Neon, Supabase y Render entregan URLs "postgres://..." o "postgresql://...".

    SQLAlchemy necesita saber QUÉ driver usar, así que lo añadimos nosotros
    ("postgresql+psycopg://"). Así puedes pegar la URL del proveedor tal cual.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    environment: str = "development"  # "production" activa comprobaciones extra

    # Conexión que usa la API en tiempo de ejecución. En producción debe ser un
    # rol restringido (sin BYPASSRLS), para que Row Level Security se aplique.
    database_url: str = "postgresql+psycopg://rentacar:rentacar@localhost:5433/rentacar"

    # Opcional: conexión con permisos de dueño, solo para aplicar migraciones.
    # Si no se define, se usa DATABASE_URL_UNPOOLED (la conexión DIRECTA que
    # escribe Neon: el DDL es más seguro sin pasar por el pooler) y, si tampoco
    # existe, database_url.
    migrations_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MIGRATIONS_DATABASE_URL", "DATABASE_URL_UNPOOLED"),
    )

    secret_key: str = _INSECURE_DEFAULT_KEY  # firma los JWT
    access_token_expire_minutes: int = 60 * 8

    # Orígenes del frontend permitidos (CORS), separados por comas.
    cors_origins: str = "http://localhost:5173"

    # Las fechas de alquiler son "días de calendario" de la agencia, así que
    # "hoy" debe calcularse en SU zona horaria, no en la del servidor (UTC).
    timezone: str = "America/Caracas"

    # Política de recargo por retraso (suposición de negocio configurable).
    late_fee_multiplier: Decimal = Decimal("1.5")

    # Máximo de intentos de login/registro por IP y ventana (0 = sin límite).
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 60

    @field_validator("database_url", "migrations_database_url")
    @classmethod
    def _fix_driver(cls, value: str | None) -> str | None:
        return _normalize_db_url(value) if value else value

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        # Falla al arrancar (mejor que descubrirlo tras un incidente) si alguien
        # despliega en producción con la clave de ejemplo o una clave corta.
        if self.environment == "production" and (self.secret_key == _INSECURE_DEFAULT_KEY or len(self.secret_key) < 32):
            raise ValueError("SECRET_KEY must be set to a random value of 32+ characters in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

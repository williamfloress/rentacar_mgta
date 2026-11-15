"""Traducción de errores de PostgreSQL a respuestas HTTP con sentido.

Filosofía: la base de datos es el árbitro final de la integridad. La API no
intenta "adivinar" antes si algo va a chocar (eso tendría condiciones de
carrera); lo intenta y, si PostgreSQL lo rechaza, convierte el error técnico
en un 409 Conflict claro para quien consume la API.
"""

from sqlalchemy.exc import IntegrityError

# Códigos SQLSTATE: https://www.postgresql.org/docs/current/errcodes-appendix.html
UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"
EXCLUSION_VIOLATION = "23P01"


def pg_code(exc: IntegrityError) -> str | None:
    """Extrae el código SQLSTATE del error original del driver (psycopg)."""
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(getattr(orig, "diag", None), "sqlstate", None)

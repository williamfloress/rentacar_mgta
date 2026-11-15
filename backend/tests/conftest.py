"""Configuración común de las pruebas.

Las variables de entorno se fijan AQUÍ, antes de que ningún test importe `app`,
porque la configuración y el motor de base de datos se crean al importar.

Las pruebas de integración usan una base de datos TEMPORAL (`rentacar_test`)
que se crea y se destruye en cada ejecución: nunca tocan la base de desarrollo.
"""

import os

from sqlalchemy.engine import make_url

# Servidor PostgreSQL con un usuario administrador (con docker compose: el rol "rentacar").
ADMIN_URL = make_url(
    os.environ.get("TEST_DATABASE_ADMIN_URL", "postgresql+psycopg://rentacar:rentacar@localhost:5433/postgres")
)
TEST_DB = "rentacar_test"
APP_ROLE, APP_ROLE_PASSWORD = "rentacar_test_app", "test-only-password"

OWNER_TEST_URL = ADMIN_URL.set(database=TEST_DB)
# La API se conecta con un rol RESTRINGIDO, igual que en producción: así RLS se aplica de verdad.
APP_TEST_URL = OWNER_TEST_URL.set(username=APP_ROLE, password=APP_ROLE_PASSWORD)

os.environ.update(
    ENVIRONMENT="test",
    DATABASE_URL=APP_TEST_URL.render_as_string(hide_password=False),
    MIGRATIONS_DATABASE_URL=OWNER_TEST_URL.render_as_string(hide_password=False),
    SECRET_KEY="test-secret-key-that-is-long-enough-0123456789",
    AUTH_RATE_LIMIT_ATTEMPTS="0",  # se activa solo en la prueba que lo comprueba
    TIMEZONE="America/Caracas",
)

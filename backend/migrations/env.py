"""Entorno de Alembic: decide a qué base de datos aplicar las migraciones."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
# Si existe MIGRATIONS_DATABASE_URL (conexión con permisos de dueño) se usa esa;
# la API, en cambio, corre con un rol restringido. Ver docs/03-despliegue-gratuito.md.
url = settings.migrations_database_url or settings.database_url

# No usamos autogenerate (el esquema vive en archivos .sql escritos a mano porque
# incluye EXCLUDE y RLS, que el ORM no modela), por eso target_metadata es None.
target_metadata = None


def run_migrations_online() -> None:
    engine = create_engine(
        url,
        poolclass=pool.NullPool,  # una sola conexión, sin pool, para el proceso de migración
        connect_args={"prepare_threshold": None},
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()

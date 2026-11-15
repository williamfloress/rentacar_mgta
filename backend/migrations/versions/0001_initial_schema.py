"""initial schema

Aplica el esquema definido en migrations/sql/0001_initial_schema.sql.

El SQL se ejecuta SENTENCIA POR SENTENCIA (separadas por líneas "-- @@") dentro
de la transacción de Alembic. PostgreSQL admite DDL transaccional: si una
sentencia falla, se revierte toda la migración y la base queda intacta.
"""

import re
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _statements(filename: str) -> list[str]:
    script = (SQL_DIR / filename).read_text(encoding="utf-8")
    chunks = [chunk.strip() for chunk in re.split(r"(?m)^-- @@\s*$", script)]
    # Se descartan los trozos que solo contienen comentarios o líneas vacías.
    return [
        chunk
        for chunk in chunks
        if any(line.strip() and not line.strip().startswith("--") for line in chunk.splitlines())
    ]


def _run(filename: str) -> None:
    connection = op.get_bind()
    for statement in _statements(filename):
        # exec_driver_sql envía el texto tal cual al driver: no interpreta ":" ni
        # "%" como parámetros (a diferencia de sqlalchemy.text), lo que protege
        # sentencias como "...::uuid" o los cuerpos $$ ... $$ de las funciones.
        connection.exec_driver_sql(statement)


def upgrade() -> None:
    _run("0001_initial_schema.sql")


def downgrade() -> None:
    _run("0001_initial_schema_down.sql")

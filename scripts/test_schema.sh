#!/usr/bin/env bash
# =====================================================================
# Prueba el esquema SQL contra un PostgreSQL REAL.
#
# Qué hace:
#   1. Crea una base de datos temporal y un rol SIN privilegios especiales
#      (igual que el que usará la API: no superusuario, sin BYPASSRLS).
#   2. Aplica backend/migrations/sql/0001_initial_schema.sql
#   3. Ejecuta backend/tests/sql/constraints_test.sql como ese rol.
#
# Uso (necesita el cliente psql y un usuario administrador de PostgreSQL):
#   PGHOST=localhost PGPORT=5432 PGUSER=postgres PGPASSWORD=postgres \
#       ./scripts/test_schema.sh
#
# Con docker compose:  docker compose up -d db  y luego el comando de arriba
# con las credenciales de docker-compose.yml.
# =====================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="rentacar_schema_test"
ROLE="rentacar_test_app"
ROLE_PASSWORD="test-only-password"

admin() { psql -v ON_ERROR_STOP=1 -X -q "$@"; }

echo ">> Preparando base de datos temporal y rol restringido"
admin -d postgres -c "DROP DATABASE IF EXISTS ${DB}"
admin -d postgres -c "DROP ROLE IF EXISTS ${ROLE}"
admin -d postgres -c "CREATE ROLE ${ROLE} LOGIN PASSWORD '${ROLE_PASSWORD}' NOSUPERUSER NOBYPASSRLS"
admin -d postgres -c "CREATE DATABASE ${DB}"

echo ">> Aplicando el esquema"
admin -d "${DB}" -f "${ROOT}/backend/migrations/sql/0001_initial_schema.sql"
admin -d "${DB}" -c "GRANT USAGE ON SCHEMA public TO ${ROLE}" \
                 -c "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${ROLE}"

echo ">> Ejecutando pruebas como rol restringido (RLS activo)"
PGPASSWORD="${ROLE_PASSWORD}" psql -X -q -U "${ROLE}" -d "${DB}" \
    -f "${ROOT}/backend/tests/sql/constraints_test.sql" 2>&1 \
    | sed -e 's/^psql:.*NOTICE:  //' -e 's/^NOTICE:  //'

echo ">> Limpiando"
admin -d postgres -c "DROP DATABASE ${DB}"
admin -d postgres -c "DROP ROLE ${ROLE}"

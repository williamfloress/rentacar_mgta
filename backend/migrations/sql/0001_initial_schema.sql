-- =====================================================================
-- rent-a-CAR · Esquema inicial (migración 0001)
-- =====================================================================
-- Este archivo es la ÚNICA fuente de verdad del esquema. Lo ejecuta
-- Alembic (ver migrations/versions/0001_initial_schema.py) y también se
-- puede aplicar directamente con psql (así lo hace scripts/test_schema.sh).
--
-- Las líneas "-- @@" separan sentencias: Alembic las usa para ejecutar
-- una a una (así no dependemos de que el driver acepte varias sentencias
-- en una sola llamada). Para psql son simples comentarios.
--
-- Tres ideas de diseño que hacen especial a este esquema:
--   1) MULTI-TENANT: cada fila pertenece a una agencia (tenant_id).
--   2) INTEGRIDAD EN LA BASE DE DATOS: el "no doble reserva" lo garantiza
--      PostgreSQL con una restricción EXCLUDE, no el código de la app.
--   3) DEFENSA EN PROFUNDIDAD: Row Level Security (RLS) impide que una
--      agencia lea o escriba filas de otra, aunque la app tuviera un bug.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS btree_gist;
-- @@
-- btree_gist permite combinar igualdad (=) sobre columnas normales con
-- operadores de rangos (&&) dentro de UN mismo índice GiST. Es lo que
-- necesita la restricción anti-solapamiento de la tabla rentals.

-- ---------------------------------------------------------------------
-- Contexto de tenant para RLS
-- ---------------------------------------------------------------------
-- La API ejecuta, al inicio de cada transacción:
--     SELECT set_config('app.tenant_id', '<uuid-de-la-agencia>', true);
-- y las políticas RLS comparan contra esta función.
-- current_setting(..., true) devuelve NULL si el parámetro no existe, así
-- que, sin contexto, tenant_id = NULL es falso y NO se ve ninguna fila.
CREATE FUNCTION app_tenant_id() RETURNS uuid
LANGUAGE sql STABLE
AS $$ SELECT nullif(current_setting('app.tenant_id', true), '')::uuid $$;
-- @@

CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END
$$;
-- @@

-- ---------------------------------------------------------------------
-- tenants: una fila por agencia de alquiler
-- ---------------------------------------------------------------------
CREATE TABLE tenants (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL CHECK (length(trim(name)) > 0),
    currency    char(3) NOT NULL DEFAULT 'USD',
    created_at  timestamptz NOT NULL DEFAULT now()
);
-- @@

-- ---------------------------------------------------------------------
-- users: personal de la agencia (dueño o agente)
-- ---------------------------------------------------------------------
-- El email es único a nivel GLOBAL (no por agencia) porque el login se
-- hace solo con email + contraseña. La restricción CHECK obliga a
-- guardarlo en minúsculas para que "A@x.com" y "a@x.com" no sean dos
-- cuentas distintas.
CREATE TABLE users (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    email          text NOT NULL UNIQUE CHECK (email = lower(email)),
    password_hash  text NOT NULL,
    full_name      text NOT NULL,
    role           text NOT NULL CHECK (role IN ('owner', 'agent')),
    is_active      boolean NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now()
);
-- @@
CREATE INDEX users_tenant_idx ON users (tenant_id);
-- @@

-- ---------------------------------------------------------------------
-- vehicles
-- ---------------------------------------------------------------------
-- UNIQUE (tenant_id, id) parece redundante (id ya es PK) pero es
-- necesario: permite que otras tablas referencien el PAR (tenant_id, id)
-- con una clave foránea compuesta. Así un alquiler de la agencia B no
-- puede apuntar a un vehículo de la agencia A ni por error ni por ataque.
CREATE TABLE vehicles (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    plate       text NOT NULL CHECK (length(trim(plate)) > 0),
    brand       text NOT NULL,
    model       text NOT NULL,
    color       text,
    year        smallint NOT NULL CHECK (year BETWEEN 1950 AND 2100),
    daily_rate  numeric(10, 2) NOT NULL CHECK (daily_rate > 0),
    status      text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'maintenance', 'retired')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, plate),
    UNIQUE (tenant_id, id)
);
-- @@

-- ---------------------------------------------------------------------
-- customers
-- ---------------------------------------------------------------------
CREATE TABLE customers (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    document_id  text NOT NULL CHECK (length(trim(document_id)) > 0),
    full_name    text NOT NULL,
    phone        text,
    email        text,
    address      text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, document_id),
    UNIQUE (tenant_id, id)
);
-- @@

-- ---------------------------------------------------------------------
-- rentals: el corazón del sistema
-- ---------------------------------------------------------------------
-- * Las fechas son un rango SEMIABIERTO [start_date, end_date):
--   el día de devolución no cuenta como día ocupado. Por eso un alquiler
--   del 10 al 15 y otro del 15 al 20 NO se solapan (el carro vuelve el
--   15 y sale de nuevo ese mismo día).
-- * daily_rate_snapshot guarda la tarifa vigente AL ALQUILAR: si mañana
--   sube el precio del carro, los alquileres existentes no cambian.
-- * La restricción rentals_no_overlap es la garantía anti-doble-reserva:
--   para un mismo vehículo, dos alquileres 'reserved'/'active' no pueden
--   tener rangos de fechas que se crucen. Al ser la propia base de datos
--   quien lo impide, es imposible violarlo ni siquiera con dos peticiones
--   simultáneas (race condition) o un bug en la aplicación.
--   Los alquileres 'returned' y 'cancelled' quedan fuera (cláusula WHERE),
--   así que liberan el vehículo.
CREATE TABLE rentals (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    vehicle_id           uuid NOT NULL,
    customer_id          uuid NOT NULL,
    start_date           date NOT NULL,
    end_date             date NOT NULL,
    daily_rate_snapshot  numeric(10, 2) NOT NULL CHECK (daily_rate_snapshot > 0),
    total_amount         numeric(12, 2) NOT NULL CHECK (total_amount >= 0),
    late_fee             numeric(12, 2) NOT NULL DEFAULT 0 CHECK (late_fee >= 0),
    status               text NOT NULL DEFAULT 'reserved'
                         CHECK (status IN ('reserved', 'active', 'returned', 'cancelled')),
    returned_at          timestamptz,
    notes                text,
    created_by           uuid REFERENCES users (id) ON DELETE SET NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT rentals_dates_valid CHECK (end_date > start_date),

    CONSTRAINT rentals_vehicle_fk
        FOREIGN KEY (tenant_id, vehicle_id) REFERENCES vehicles (tenant_id, id),
    CONSTRAINT rentals_customer_fk
        FOREIGN KEY (tenant_id, customer_id) REFERENCES customers (tenant_id, id),

    CONSTRAINT rentals_no_overlap EXCLUDE USING gist (
        vehicle_id WITH =,
        daterange(start_date, end_date, '[)') WITH &&
    ) WHERE (status IN ('reserved', 'active'))
);
-- @@
CREATE INDEX rentals_tenant_status_idx ON rentals (tenant_id, status);
-- @@
CREATE INDEX rentals_tenant_customer_idx ON rentals (tenant_id, customer_id);
-- @@
CREATE INDEX rentals_tenant_vehicle_idx ON rentals (tenant_id, vehicle_id);
-- @@
CREATE INDEX rentals_tenant_start_idx ON rentals (tenant_id, start_date);
-- @@

-- ---------------------------------------------------------------------
-- audit_log: registro de "quién hizo qué" (solo se añade, nunca se edita)
-- ---------------------------------------------------------------------
CREATE TABLE audit_log (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    user_id     uuid REFERENCES users (id) ON DELETE SET NULL,
    action      text NOT NULL,
    entity      text NOT NULL,
    entity_id   uuid,
    detail      jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
-- @@
CREATE INDEX audit_log_tenant_created_idx ON audit_log (tenant_id, created_at DESC);
-- @@

-- ---------------------------------------------------------------------
-- Triggers: mantener updated_at al día
-- ---------------------------------------------------------------------
CREATE TRIGGER vehicles_set_updated_at BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- @@
CREATE TRIGGER customers_set_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- @@
CREATE TRIGGER rentals_set_updated_at BEFORE UPDATE ON rentals
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- @@

-- ---------------------------------------------------------------------
-- Row Level Security (aislamiento entre agencias)
-- ---------------------------------------------------------------------
-- ENABLE activa RLS; FORCE hace que también aplique al dueño de la tabla
-- (por defecto el dueño se la salta). Los superusuarios y los roles con
-- BYPASSRLS siempre se la saltan: por eso en producción la app debe
-- conectarse con un rol restringido (ver scripts/create_app_role.sql y
-- docs/03-despliegue-gratuito.md).
ALTER TABLE tenants   ENABLE ROW LEVEL SECURITY;
-- @@
ALTER TABLE tenants   FORCE ROW LEVEL SECURITY;
-- @@
ALTER TABLE users     ENABLE ROW LEVEL SECURITY;
-- @@
ALTER TABLE users     FORCE ROW LEVEL SECURITY;
-- @@
ALTER TABLE vehicles  ENABLE ROW LEVEL SECURITY;
-- @@
ALTER TABLE vehicles  FORCE ROW LEVEL SECURITY;
-- @@
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
-- @@
ALTER TABLE customers FORCE ROW LEVEL SECURITY;
-- @@
ALTER TABLE rentals   ENABLE ROW LEVEL SECURITY;
-- @@
ALTER TABLE rentals   FORCE ROW LEVEL SECURITY;
-- @@
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
-- @@
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
-- @@

-- USING   = qué filas se pueden VER / modificar / borrar.
-- WITH CHECK = qué filas se pueden INSERTAR / dejar tras un UPDATE.
CREATE POLICY tenant_isolation ON tenants
    USING (id = app_tenant_id()) WITH CHECK (id = app_tenant_id());
-- @@
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id());
-- @@
CREATE POLICY tenant_isolation ON vehicles
    USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id());
-- @@
CREATE POLICY tenant_isolation ON customers
    USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id());
-- @@
CREATE POLICY tenant_isolation ON rentals
    USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id());
-- @@

-- Login: cuando alguien inicia sesión todavía no sabemos su agencia. En
-- lugar de abrir la tabla users por completo, la API declara el email
-- que está buscando (app.login_email) y esta política permite ver SOLO
-- esa fila. Las políticas permisivas se combinan con OR.
CREATE POLICY login_lookup ON users FOR SELECT
    USING (email = current_setting('app.login_email', true));
-- @@

-- audit_log es "solo añadir": se crean políticas únicamente para SELECT e
-- INSERT. Con RLS activado, un comando sin política aplicable no ve
-- ninguna fila, así que UPDATE y DELETE no pueden tocar nada.
CREATE POLICY audit_select ON audit_log FOR SELECT
    USING (tenant_id = app_tenant_id());
-- @@
CREATE POLICY audit_insert ON audit_log FOR INSERT
    WITH CHECK (tenant_id = app_tenant_id());

-- =====================================================================
-- Pruebas del esquema: verifican que las GARANTÍAS vivan en la base de
-- datos. Se ejecuta con un rol SIN privilegios especiales (no superusuario,
-- sin BYPASSRLS), igual que lo haría la API en producción.
-- Lo lanza scripts/test_schema.sh. Si algo falla, psql termina con error.
-- =====================================================================
\set ON_ERROR_STOP on
\set QUIET on
SET client_min_messages = notice;

-- ---------- Datos de partida: dos agencias (A y B) ----------
SET app.tenant_id = '00000000-0000-0000-0000-00000000000a';
INSERT INTO tenants (id, name) VALUES ('00000000-0000-0000-0000-00000000000a', 'Agencia A');
INSERT INTO users (tenant_id, email, password_hash, full_name, role)
    VALUES ('00000000-0000-0000-0000-00000000000a', 'a@example.com', 'hash', 'Dueño A', 'owner');
INSERT INTO vehicles (id, tenant_id, plate, brand, model, year, daily_rate)
    VALUES ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-00000000000a',
            'AAA111', 'Toyota', 'Corolla', 2020, 40);
INSERT INTO customers (id, tenant_id, document_id, full_name)
    VALUES ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-00000000000a',
            'V-1', 'Cliente A');

SET app.tenant_id = '00000000-0000-0000-0000-00000000000b';
INSERT INTO tenants (id, name) VALUES ('00000000-0000-0000-0000-00000000000b', 'Agencia B');
INSERT INTO vehicles (id, tenant_id, plate, brand, model, year, daily_rate)
    VALUES ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-00000000000b',
            'BBB222', 'Honda', 'Civic', 2021, 50);
INSERT INTO customers (id, tenant_id, document_id, full_name)
    VALUES ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-00000000000b',
            'V-2', 'Cliente B');

-- ================= A partir de aquí actuamos como la agencia A =================
SET app.tenant_id = '00000000-0000-0000-0000-00000000000a';

-- 1) Un alquiler normal se acepta (10 al 15 de enero de 2030)
INSERT INTO rentals (id, tenant_id, vehicle_id, customer_id, start_date, end_date,
                     daily_rate_snapshot, total_amount)
VALUES ('00000000-0000-0000-0000-0000000000f1', '00000000-0000-0000-0000-00000000000a',
        '00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000c1',
        '2030-01-10', '2030-01-15', 40, 200);

-- 2) Un alquiler que se SOLAPA con el anterior (12 al 20) debe ser rechazado
DO $$
BEGIN
    INSERT INTO rentals (tenant_id, vehicle_id, customer_id, start_date, end_date,
                         daily_rate_snapshot, total_amount)
    VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a1',
            '00000000-0000-0000-0000-0000000000c1', '2030-01-12', '2030-01-20', 40, 320);
    RAISE EXCEPTION 'FALLO: se aceptó un alquiler solapado';
EXCEPTION WHEN exclusion_violation THEN
    RAISE NOTICE 'OK 2: alquiler solapado rechazado (23P01 exclusion_violation)';
END $$;

-- 3) Un alquiler que EMPIEZA el día de devolución (15 al 20) es válido:
--    el rango es semiabierto, el carro vuelve el 15 y sale otra vez ese día.
INSERT INTO rentals (id, tenant_id, vehicle_id, customer_id, start_date, end_date,
                     daily_rate_snapshot, total_amount)
VALUES ('00000000-0000-0000-0000-0000000000f2', '00000000-0000-0000-0000-00000000000a',
        '00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000c1',
        '2030-01-15', '2030-01-20', 40, 200);
DO $$ BEGIN RAISE NOTICE 'OK 3: alquileres consecutivos (15 = devolución = nueva salida) aceptados'; END $$;

-- 4) Al CANCELAR el primero, sus fechas quedan libres de nuevo
UPDATE rentals SET status = 'cancelled' WHERE id = '00000000-0000-0000-0000-0000000000f1';
INSERT INTO rentals (tenant_id, vehicle_id, customer_id, start_date, end_date,
                     daily_rate_snapshot, total_amount)
VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a1',
        '00000000-0000-0000-0000-0000000000c1', '2030-01-11', '2030-01-14', 40, 120);
DO $$ BEGIN RAISE NOTICE 'OK 4: un alquiler cancelado libera el vehículo'; END $$;

-- 5) Fechas incoherentes (fin <= inicio) violan el CHECK
DO $$
BEGIN
    INSERT INTO rentals (tenant_id, vehicle_id, customer_id, start_date, end_date,
                         daily_rate_snapshot, total_amount)
    VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a1',
            '00000000-0000-0000-0000-0000000000c1', '2031-05-10', '2031-05-10', 40, 0);
    RAISE EXCEPTION 'FALLO: se aceptaron fechas incoherentes';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'OK 5: end_date <= start_date rechazado (check_violation)';
END $$;

-- 6) La placa es única POR agencia (misma placa en dos agencias sí es válida)
DO $$
BEGIN
    INSERT INTO vehicles (tenant_id, plate, brand, model, year, daily_rate)
    VALUES ('00000000-0000-0000-0000-00000000000a', 'AAA111', 'Kia', 'Rio', 2019, 30);
    RAISE EXCEPTION 'FALLO: se aceptó una placa duplicada en la misma agencia';
EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'OK 6: placa duplicada dentro de la misma agencia rechazada';
END $$;

-- ================= Aislamiento entre agencias =================
SET app.tenant_id = '00000000-0000-0000-0000-00000000000b';

-- 7) La agencia B no ve los datos de A
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM vehicles WHERE plate = 'AAA111';
    IF n <> 0 THEN RAISE EXCEPTION 'FALLO: B ve vehículos de A (%)', n; END IF;
    SELECT count(*) INTO n FROM rentals;
    IF n <> 0 THEN RAISE EXCEPTION 'FALLO: B ve alquileres de A (%)', n; END IF;
    SELECT count(*) INTO n FROM vehicles;
    IF n <> 1 THEN RAISE EXCEPTION 'FALLO: B debería ver solo su vehículo (%)', n; END IF;
    RAISE NOTICE 'OK 7: RLS oculta los datos de otras agencias';
END $$;

-- 8) B no puede insertar filas a nombre de A (WITH CHECK de RLS)
DO $$
BEGIN
    INSERT INTO vehicles (tenant_id, plate, brand, model, year, daily_rate)
    VALUES ('00000000-0000-0000-0000-00000000000a', 'HACK01', 'X', 'Y', 2020, 10);
    RAISE EXCEPTION 'FALLO: B insertó un vehículo en la agencia A';
EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'OK 8: RLS impide escribir filas de otra agencia (42501)';
END $$;

-- 9) B no puede alquilar un vehículo de A: la FK compuesta (tenant_id, vehicle_id) lo impide
DO $$
BEGIN
    INSERT INTO rentals (tenant_id, vehicle_id, customer_id, start_date, end_date,
                         daily_rate_snapshot, total_amount)
    VALUES ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-0000000000a1',
            '00000000-0000-0000-0000-0000000000c2', '2032-01-01', '2032-01-05', 40, 160);
    RAISE EXCEPTION 'FALLO: B alquiló un vehículo de A';
EXCEPTION WHEN foreign_key_violation THEN
    RAISE NOTICE 'OK 9: la FK compuesta impide referenciar datos de otra agencia (23503)';
END $$;

-- 10) Sin contexto de agencia no se ve nada (falla "cerrada", no abierta)
SET app.tenant_id = '';
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM vehicles;
    IF n <> 0 THEN RAISE EXCEPTION 'FALLO: sin contexto se ven % vehículos', n; END IF;
    SELECT count(*) INTO n FROM users;
    IF n <> 0 THEN RAISE EXCEPTION 'FALLO: sin contexto se ven % usuarios', n; END IF;
    RAISE NOTICE 'OK 10: sin app.tenant_id no se ve ninguna fila';
END $$;

-- 11) Login: solo se ve el usuario cuyo email se declara en app.login_email
SET app.login_email = 'a@example.com';
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM users;
    IF n <> 1 THEN RAISE EXCEPTION 'FALLO: login_lookup devolvió % filas', n; END IF;
    RAISE NOTICE 'OK 11: la política de login expone únicamente el usuario buscado';
END $$;
SET app.login_email = 'otro@example.com';
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM users;
    IF n <> 0 THEN RAISE EXCEPTION 'FALLO: login_lookup filtró de más (%)', n; END IF;
    RAISE NOTICE 'OK 11b: un email inexistente no revela nada';
END $$;
SET app.login_email = '';

-- ================= audit_log es solo-añadir =================
SET app.tenant_id = '00000000-0000-0000-0000-00000000000a';
INSERT INTO audit_log (tenant_id, action, entity) VALUES
    ('00000000-0000-0000-0000-00000000000a', 'rental.created', 'rental');
DO $$
DECLARE n integer;
BEGIN
    UPDATE audit_log SET action = 'manipulado';
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 0 THEN RAISE EXCEPTION 'FALLO: se modificaron % filas de auditoría', n; END IF;
    DELETE FROM audit_log;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 0 THEN RAISE EXCEPTION 'FALLO: se borraron % filas de auditoría', n; END IF;
    SELECT count(*) INTO n FROM audit_log;
    IF n <> 1 THEN RAISE EXCEPTION 'FALLO: la fila de auditoría debería seguir ahí'; END IF;
    RAISE NOTICE 'OK 12: audit_log no se puede editar ni borrar desde la app';
END $$;

\echo
\echo '=== TODAS LAS PRUEBAS SQL PASARON ==='

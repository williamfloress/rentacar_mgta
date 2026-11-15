-- Reversión de la migración 0001 (se ejecuta con "alembic downgrade base").
-- No elimina la extensión btree_gist: otras bases/objetos podrían usarla.
DROP TABLE IF EXISTS audit_log;
-- @@
DROP TABLE IF EXISTS rentals;
-- @@
DROP TABLE IF EXISTS customers;
-- @@
DROP TABLE IF EXISTS vehicles;
-- @@
DROP TABLE IF EXISTS users;
-- @@
DROP TABLE IF EXISTS tenants;
-- @@
DROP FUNCTION IF EXISTS set_updated_at();
-- @@
DROP FUNCTION IF EXISTS app_tenant_id();

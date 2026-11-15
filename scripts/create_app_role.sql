-- =====================================================================
-- Crea el rol RESTRINGIDO con el que se conecta la API.
--
-- Por qué existe: Row Level Security no se aplica a superusuarios ni a roles con
-- BYPASSRLS. En proveedores como Neon o Supabase, el rol "por defecto" que te dan
-- suele saltarse RLS. Si la API usara ese rol, el aislamiento entre agencias
-- dependería SOLO de los filtros del código. Con este rol, la base de datos
-- vuelve a ser la segunda barrera.
--
-- Cómo usarlo:
--   * Docker local: docker-compose.yml lo ejecuta solo, al crear la base.
--   * Neon/Supabase: ejecútalo UNA vez con el rol dueño (el que aplica las
--     migraciones), DESPUÉS de la primera migración, y CAMBIA LA CONTRASEÑA:
--       psql "<URL-del-rol-dueño>" -f scripts/create_app_role.sql
--     Luego usa este rol en DATABASE_URL y deja el dueño en MIGRATIONS_DATABASE_URL.
-- =====================================================================
CREATE ROLE rentacar_app LOGIN PASSWORD 'rentacar_app_dev'   -- <- CAMBIAR en producción
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

GRANT USAGE ON SCHEMA public TO rentacar_app;

-- Permisos sobre las tablas que ya existan...
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rentacar_app;

-- ...y sobre las que las migraciones creen en el futuro (las crea el rol que
-- ejecuta este script, que es el dueño).
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO rentacar_app;

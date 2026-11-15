# 03 · Despliegue gratuito del MVP

Objetivo: tener el MVP en internet **sin pagar y sin tarjeta** (o con tarjeta solo de
verificación), con una arquitectura que se pueda migrar sin reescribir nada.

```
Navegador ──► Frontend (Vercel/Netlify)  ──►  API FastAPI en Docker (Render)  ──►  PostgreSQL (Neon / Supabase)
```

> ⚠️ Los planes gratuitos cambian con frecuencia. Las cifras de abajo corresponden a
> noviembre de 2026; **verifica los límites en la documentación oficial el día que despliegues**.

## Por qué esta combinación

| Pieza | Elección | Motivo | Limitación a conocer |
|---|---|---|---|
| API | Render, servicio web Docker, plan gratuito | No pide tarjeta; despliega desde GitHub | Se duerme tras 15 min sin tráfico y tarda ~1 min en despertar. Tiene 750 horas gratis al mes por workspace (suficiente para un servicio). |
| Base de datos | Neon o Supabase (PostgreSQL gratuito) | La BD gratuita de Render **expira a los 30 días**, así que no sirve para un demo duradero | Pueden suspender la BD por inactividad y tienen cuotas; revisa su plan actual. |
| Frontend | Vercel, Netlify o sitio estático de Render | Los sitios estáticos no se duermen | — |

**Alternativa:** Google Cloud Run (2 millones de peticiones gratis al mes, escala a cero)
exige tarjeta pero no cobra dentro del tope gratuito. Como la app va en Docker, el cambio
es cuestión de horas.

## Paso a paso

### 1. Crear la base de datos (Neon o Supabase)

1. Crea un proyecto y una base de datos PostgreSQL. Elige una región cercana a la de Render
   (por ejemplo, ambas en EE. UU. este).
2. Copia la **cadena de conexión** del rol dueño. Pegarla tal cual funciona: la API convierte
   `postgres://` o `postgresql://` en `postgresql+psycopg://` automáticamente.
3. Si el proveedor ofrece una conexión *pooled* (por ejemplo con `-pooler` en el host de Neon),
   puedes usarla: el código ya desactiva las sentencias preparadas
   (`prepare_threshold=None`) que esos poolers no soportan.
4. Asegúrate de que la cadena incluya `sslmode=require` (los proveedores suelen añadirlo).

### 2. Entender los dos roles de base de datos (importante)

La API usa **dos conexiones distintas**:

| Variable | Rol | Para qué |
|---|---|---|
| `MIGRATIONS_DATABASE_URL` | **Dueño** (el que te da el proveedor) | Solo crear/modificar tablas al arrancar |
| `DATABASE_URL` | **`rentacar_app`** (restringido) | Todas las consultas de la API |

**¿Por qué?** Row Level Security no se aplica a superusuarios ni a roles con `BYPASSRLS`, y el
rol por defecto de estos proveedores suele estar en ese caso. Si la API se conectara con él, el
aislamiento entre agencias dependería **solo** del código. Con el rol restringido, la base de
datos vuelve a ser la segunda barrera. Se probó: ejecutadas como superusuario, las pruebas de
aislamiento fallan.

Como el rol restringido necesita que las tablas ya existan para recibir permisos, el orden es:
**primer despliegue con el rol dueño → crear el rol → segundo despliegue con el rol restringido.**
Los pasos 4 y 5 lo detallan.

### 3. Subir el proyecto a GitHub

```bash
git init
git add .
git commit -m "MVP backend: esqueleto, esquema y pruebas"
git remote add origin <tu-repositorio>
git push -u origin main
```

Comprueba antes que `.env` **no** esté incluido (el `.gitignore` ya lo excluye).

### 4. Primer despliegue en Render (con el rol dueño)

1. En Render: **New → Blueprint**, y selecciona el repositorio. Render lee `render.yaml`.
2. Define las variables marcadas con `sync: false`. **Para este primer despliegue, pon la URL
   del rol dueño en las dos primeras:**

| Variable | Valor (primer despliegue) |
|---|---|
| `DATABASE_URL` | URL del rol **dueño** (temporal) |
| `MIGRATIONS_DATABASE_URL` | URL del rol **dueño** |
| `CORS_ORIGINS` | URL de tu frontend (p. ej. `https://rent-a-car.vercel.app`) |

   `SECRET_KEY` se genera sola. `ENVIRONMENT=production` activa una comprobación: la API
   **se niega a arrancar** con una clave débil.
3. Despliega. En el primer arranque, el contenedor ejecuta `alembic upgrade head` (crea las
   tablas) y luego levanta la API.

> `render.yaml` no se pudo validar contra Render desde el entorno de desarrollo: si algún
> campo cambió, la plataforma lo indicará al importar el *blueprint*. El panel web permite
> crear el servicio a mano con los mismos valores (Docker, ruta `backend/Dockerfile`,
> contexto `backend`, comprobación de salud `/health`).

### 4b. Crear el rol restringido y hacer el segundo despliegue

Desde tu PC, con `psql` y la URL del rol dueño:

1. Edita `scripts/create_app_role.sql` y **cambia la contraseña** de `rentacar_app`.
2. Ejecútalo: `psql "<URL-rol-dueño>" -f scripts/create_app_role.sql`
3. Construye la URL del rol restringido: es la misma cadena de conexión, cambiando usuario
   (`rentacar_app`) y contraseña.
4. En Render, **cambia `DATABASE_URL` a esa URL restringida** y redespliega.
   `MIGRATIONS_DATABASE_URL` se queda con el rol dueño.

### 5. Comprobar que todo funciona (tras el segundo despliegue)

1. `https://<tu-servicio>.onrender.com/health` → `{"status":"ok"}`
2. `https://<tu-servicio>.onrender.com/health/db` → `{"status":"ok","database":"reachable"}`
3. `https://<tu-servicio>.onrender.com/docs` → Swagger; prueba `POST /auth/register`.

Si `/health/db` falla, el problema suele ser la URL (usuario, contraseña o `sslmode`).
Si el registro funciona pero luego no ves tus datos, revisa que `DATABASE_URL` use el rol
restringido y que las políticas RLS estén creadas (`\d vehicles` en `psql` muestra las políticas).

### 6. Panel web y demo pública

`render.yaml` también crea el panel como **sitio estático** (`rent-a-car-web`):

1. Define `VITE_API_URL` con la URL pública de la API (`https://<tu-servicio>.onrender.com`).
   Vite la incrusta en el JavaScript **al compilar**: si la cambias, hay que redesplegar el sitio.
2. Añade la URL del sitio a `CORS_ORIGINS` de la API (separadas por comas si hay varias).
3. `SEED_DEMO=true` en la API recrea la agencia de demostración en cada arranque
   (`demo@rentacar.dev` / `demo-rentacar`). Como el plan gratuito se reinicia a menudo, la
   demo se "limpia" sola. Para una instalación real, elimina esa variable.

Alternativas equivalentes: Vercel o Netlify (directorio `frontend`, comando `npm run build`,
carpeta `dist`, y una regla de *rewrite* de todas las rutas a `/index.html`).

## Manejar el arranque en frío

En el plan gratuito, la primera petición tras un rato de inactividad tarda cerca de un
minuto. Mitigaciones, de más a menos recomendable:

1. **Pantalla de carga honesta** en el frontend ("despertando el servidor, puede tardar
   hasta un minuto la primera vez"). Es lo más sencillo y transparente. **Ya implementado:**
   el login muestra el aviso si la petición tarda más de 4 segundos (`useSlowFlag`).
2. **Aviso en el README** y en el portafolio: es un demo en plan gratuito.
3. Un servicio externo de *ping* periódico a `/health` mantiene la API despierta, pero es un
   parche; el límite de 750 horas permite mantener un servicio encendido todo el mes.
4. Cuando haya clientes reales, un plan de pago (unos pocos dólares al mes) elimina el problema.

## Migrar a otro proveedor

Gracias a Docker, mover la API es repetir el paso 4 en otro host (Cloud Run, Fly.io, un VPS
con Docker, etc.) con las mismas variables de entorno. La base de datos se mueve con
`pg_dump` / `pg_restore`.

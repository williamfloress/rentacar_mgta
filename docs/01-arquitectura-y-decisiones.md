# 01 · Arquitectura y decisiones

Cada decisión tiene tres partes: **qué se eligió**, **por qué** y **qué se sacrificó**.
Un buen proyecto de portafolio no es el que usa la tecnología más de moda, sino el que
sabe explicar sus compromisos.

## 1. Visión general

```mermaid
sequenceDiagram
    participant C as Cliente (navegador)
    participant A as API (FastAPI)
    participant D as PostgreSQL
    C->>A: POST /rentals  (Authorization: Bearer JWT)
    A->>A: Valida firma y caducidad del JWT
    A->>D: BEGIN; set_config('app.tenant_id', <agencia>, true)
    A->>D: SELECT usuario (RLS filtra por agencia)
    A->>A: Valida fechas y calcula el total (lógica pura)
    A->>D: INSERT INTO rentals ...
    alt fechas libres
        D-->>A: OK
        A-->>C: 201 Created
    else se cruza con otra reserva
        D-->>A: error 23P01 (exclusion_violation)
        A-->>C: 409 Conflict
    end
```

Las capas, de fuera hacia dentro: **routers** (HTTP) → **dominio** (reglas puras) →
**modelos/BD** (persistencia). Las reglas de negocio no importan FastAPI ni SQLAlchemy.

## 2. Decisiones

### 2.1 Backend: FastAPI (Python) en lugar de Spring Boot
- **Por qué:** consume poca memoria y arranca rápido, lo que importa en planes gratuitos
  (512 MB y 0,1 CPU). La documentación OpenAPI/Swagger sale gratis. Y encaja con un
  futuro módulo de analítica y predicción de demanda en el mismo lenguaje.
- **Sacrificio:** Spring Boot abre más puertas en grandes empresas y consultoras. Como todo
  va en Docker, cambiar de backend más adelante no obliga a cambiar el despliegue.

### 2.2 SQLAlchemy síncrono, no asíncrono
- **Por qué:** más simple de entender, de depurar y de razonar sobre transacciones. FastAPI
  ejecuta los endpoints síncronos en un pool de hilos, suficiente para este volumen.
- **Sacrificio:** a miles de peticiones concurrentes el modelo asíncrono rinde más. Es una
  optimización prematura para un MVP.

### 2.3 El esquema vive en SQL escrito a mano, no generado por el ORM
- **Por qué:** lo importante (la restricción `EXCLUDE`, las políticas RLS, las claves
  compuestas) el ORM no lo expresa bien. Un solo archivo `.sql` es la fuente de verdad: lo
  usa Alembic **y** lo prueba directamente `scripts/test_schema.sh`.
- **Sacrificio:** no hay *autogenerate* de migraciones; cada cambio de esquema se escribe a
  mano. Es más trabajo, pero también más control y más claridad.

### 2.4 La integridad la garantiza la base de datos, no el código
La API **no** comprueba "¿está libre el carro?" antes de insertar. Esa comprobación previa
tiene una *condición de carrera*: dos peticiones simultáneas ven "libre" a la vez y ambas
reservan. En su lugar, la API intenta insertar y la restricción `EXCLUDE` rechaza la segunda
de forma atómica. La API solo traduce el error a un `409 Conflict`.
- **Sacrificio:** acopla la regla a PostgreSQL (no es portable a MySQL). Se acepta: la
  garantía vale más que la portabilidad.

### 2.5 Multi-tenant: una base de datos, columna `tenant_id`, doble candado
- **Por qué:** una sola base compartida es la opción más barata y simple de operar para
  muchas agencias pequeñas. El aislamiento se refuerza con **dos candados independientes**:
  1. Filtro explícito `tenant_id == usuario.tenant_id` en cada consulta (`lookups.py`).
  2. **Row Level Security** en PostgreSQL: aunque el código tuviera un bug, la base no
     entrega filas de otra agencia.
- **Sacrificio:** RLS no se aplica a superusuarios ni a roles con `BYPASSRLS`. En Neon y
  Supabase el rol por defecto suele saltárselo, así que **la API debe conectarse con un rol
  restringido** (`scripts/create_app_role.sql`). Un experimento lo demuestra: ejecutadas como
  superusuario, las pruebas de aislamiento fallan. Esa es la razón de que existan dos URLs de
  conexión (`DATABASE_URL` y `MIGRATIONS_DATABASE_URL`).
- **Alternativa descartada:** una base de datos por agencia. Mayor aislamiento, pero mucho
  más coste y complejidad operativa para este tamaño.

### 2.6 Rangos de fechas semiabiertos `[inicio, fin)`
El día de devolución no cuenta como ocupado: un alquiler del 10 al 15 y otro del 15 al 20 no
se solapan (el carro vuelve el 15 y sale ese mismo día). Es el criterio habitual en el sector
y lo usan de forma coherente tres sitios: el cálculo de días, la consulta de disponibilidad y
la restricción de la base de datos.

### 2.7 Autenticación: JWT de vida corta, con el rol leído de la base de datos
- El token solo lleva `sub` (usuario) y `tid` (agencia). El **rol no va en el token**: se lee
  de la base de datos en cada petición. Así, desactivar a un empleado o cambiarle el rol
  surte efecto al instante en vez de esperar a que el token caduque.
- Contraseñas con **Argon2id**. El login verifica contra un hash de relleno si el email no
  existe, para que el tiempo de respuesta no revele qué cuentas están registradas.
- La lista de algoritmos aceptados es explícita, lo que bloquea el ataque de `alg=none`
  (comprobado en las pruebas).
- **Sacrificio:** una consulta a la BD por petición autenticada, y no hay *refresh tokens*
  ni cierre de sesión en servidor todavía (ver roadmap).

### 2.8 Dinero con `Decimal`, importes como texto en JSON
`float` no puede representar 0,1 de forma exacta; en facturación eso son céntimos que no
cuadran. Se usa `Decimal` de extremo a extremo (`numeric(10,2)` en la base de datos).
Pydantic los serializa como cadena (`"200.00"`); el frontend debe formatearlos, no sumarlos
con `parseFloat`.

### 2.9 La zona horaria de la agencia define "hoy"
Los servidores corren en UTC; Venezuela es UTC-4. Entre las 8 pm y la medianoche locales, en
UTC ya es "mañana": sin cuidado, un alquiler que vence hoy se cobraría como tardío. Por eso
`clock.today()` usa la zona configurada (`TIMEZONE`).

### 2.10 Tarifa "congelada" en cada alquiler
`daily_rate_snapshot` guarda el precio vigente al reservar. Si mañana sube la tarifa del
carro, los alquileres ya hechos no cambian. Es lo que esperaría cualquier cliente.

### 2.11 Las migraciones corren al arrancar el contenedor
Simple y suficiente para un MVP con una sola instancia: `alembic upgrade head && uvicorn`.
- **Sacrificio:** con varias instancias arrancando a la vez habría carreras; y el arranque en
  frío tarda un poco más. Al escalar, las migraciones pasan a un paso de despliegue aparte.

### 2.12 `/health` no toca la base de datos
Render lo usa para saber si el proceso está vivo. Si dependiera de la BD (que en planes
gratuitos puede estar "dormida"), la plataforma reiniciaría el servicio sin necesidad. Existe
`/health/db` aparte, para diagnóstico.

## 3. Suposiciones de negocio (cámbialas si no encajan)

Estas reglas son decisiones **mías** por falta de datos reales; conviene validarlas con
dueños de agencias reales:

- Recargo por retraso: `tarifa × 1,5 × días de retraso` (configurable con `LATE_FEE_MULTIPLIER`).
- Una reserva no puede empezar en el pasado.
- Una reserva activa no se puede cancelar; solo devolver.
- Ingresos del mes = total + recargos de alquileres `active`/`returned` que **empiezan** ese mes.
- Un vehículo en `maintenance` no se puede reservar, pero el sistema **no** revisa si ya
  tiene reservas futuras al ponerlo en mantenimiento (pendiente en el roadmap).
- El email es único en todo el sistema (no por agencia), porque el login solo pide email y contraseña.

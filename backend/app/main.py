"""Punto de entrada de la API.

Arranque local:   uvicorn app.main:app --reload
Documentación interactiva (Swagger): http://localhost:8000/docs
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.pagination import TOTAL_COUNT_HEADER
from app.routers import auth, customers, dashboard, rentals, users, vehicles

settings = get_settings()

app = FastAPI(
    title="rent-a-CAR API",
    version="1.0.0",
    description=(
        "API multi-agencia para gestionar el alquiler de vehículos: flota, clientes, "
        "reservas sin dobles reservas y métricas. Cada agencia solo accede a sus datos."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # La autenticación va en la cabecera Authorization (no en cookies), así que no
    # hace falta allow_credentials; dejarlo en False reduce la superficie de ataque.
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    # Sin esto el navegador oculta la cabecera al JavaScript y el frontend no
    # podría saber cuántas páginas hay.
    expose_headers=[TOTAL_COUNT_HEADER],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Cabeceras de seguridad básicas en toda respuesta."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(vehicles.router)
app.include_router(customers.router)
app.include_router(rentals.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness: NO toca la base de datos a propósito. Render lo usa para saber si
    el proceso está vivo; si dependiera de la BD (que puede estar "dormida" en el
    plan gratuito) la plataforma reiniciaría el servicio sin necesidad."""
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db() -> dict[str, str]:
    """Diagnóstico: comprueba que la conexión a PostgreSQL funciona."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}

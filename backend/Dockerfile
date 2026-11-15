# Imagen de la API. Funciona igual en tu PC, en Render, en Cloud Run o en un VPS:
# esa portabilidad es la razón de usar Docker.
FROM python:3.13-slim

# - sin .pyc ni buffer de salida (los logs aparecen al instante en el panel de Render)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Primero SOLO el lock de dependencias: Docker cachea esta capa y no reinstala
# mientras no cambie, aunque edites el código (builds mucho más rápidos).
# requirements.lock fija versiones EXACTAS: el build de hoy y el de dentro de un año son iguales.
COPY requirements.lock .
RUN pip install -r requirements.lock

COPY . .

# Seguridad: el proceso NO corre como root. Si alguien explotara una vulnerabilidad
# de la app, tendría muchos menos privilegios dentro del contenedor.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# 1) alembic upgrade head -> aplica las migraciones pendientes (idempotente).
# 2) si SEED_DEMO=true, (re)crea la agencia de demostración con datos de ejemplo.
# 3) arranca la API. --proxy-headers: detrás del proxy de Render, la IP del cliente
#    llega en X-Forwarded-For (la necesita el limitador de intentos de login).
# Render inyecta la variable PORT; en local usamos 8000 por defecto.
CMD ["sh", "-c", "alembic upgrade head && if [ \"$SEED_DEMO\" = \"true\" ]; then python -m app.seed; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

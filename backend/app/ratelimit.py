"""Limitación de intentos (rate limiting) para login y registro.

Frena ataques de fuerza bruta contra contraseñas: cada IP tiene un número
máximo de intentos por ventana de tiempo; al superarlo recibe 429.

Alcance consciente (documentado en docs/04-roadmap.md):
  * El contador vive EN MEMORIA del proceso. Con una sola instancia (el plan
    gratuito de Render) es suficiente; con varias, cada una contaría por su
    cuenta y habría que moverlo a Redis.
  * La IP se toma de la conexión. Detrás del proxy de Render, uvicorn se arranca
    con --proxy-headers para que esa IP sea la del cliente y no la del proxy.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings


class RateLimiter:
    """Ventana deslizante: como mucho `max_attempts` en los últimos `window_seconds`."""

    def __init__(self, max_attempts: int, window_seconds: float, clock=time.monotonic) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()  # los endpoints síncronos corren en varios hilos

    def hit(self, key: str) -> bool:
        """Registra un intento. Devuelve False si la clave ya agotó su cupo."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_attempts:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_settings = get_settings()
auth_limiter = RateLimiter(_settings.auth_rate_limit_attempts, _settings.auth_rate_limit_window_seconds)


def limit_auth_attempts(request: Request) -> None:
    """Dependencia de FastAPI para los endpoints de autenticación."""
    if _settings.auth_rate_limit_attempts <= 0:  # 0 = desactivado
        return
    client_ip = request.client.host if request.client else "unknown"
    if not auth_limiter.hit(client_ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, try again later",
            headers={"Retry-After": str(int(auth_limiter.window_seconds))},
        )

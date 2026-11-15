"""Fecha "de hoy" en la zona horaria de la agencia.

Render y la mayoría de servidores corren en UTC. Venezuela es UTC-4: entre las
8 pm y la medianoche locales, en UTC ya es "mañana". Si usáramos date.today()
a secas, un alquiler que vence hoy podría registrarse como retrasado, o una
reserva "para hoy" ser rechazada por estar "en el pasado". Por eso "hoy" se
calcula siempre con la zona horaria configurada (TIMEZONE).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def today() -> date:
    return datetime.now(ZoneInfo(get_settings().timezone)).date()

"""Conexión a PostgreSQL y contexto de agencia (tenant) para Row Level Security.

Cómo se conecta todo (la parte más importante de este archivo):

  1. La petición HTTP trae un JWT. Del JWT sale el id de la agencia.
  2. La dependencia get_current_user (deps.py) guarda ese id en `session.info`.
  3. Cada vez que la sesión abre una TRANSACCIÓN, el evento `after_begin` de
     abajo ejecuta  set_config('app.tenant_id', <id>, true).
  4. Las políticas RLS de PostgreSQL leen ese valor (función app_tenant_id())
     y solo dejan ver/escribir filas de esa agencia.

¿Por qué en `after_begin` y no una sola vez? Porque set_config(..., true) es
LOCAL A LA TRANSACCIÓN: tras un commit() la configuración desaparece. Con este
evento se reaplica automáticamente en cada transacción nueva de la misma
petición, sin que nadie tenga que acordarse.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # comprueba la conexión antes de usarla (útil con BD que se suspenden)
    pool_size=5,
    max_overflow=5,
    # Los proveedores serverless (Neon, Supabase) usan un "pooler" en modo
    # transacción que NO soporta sentencias preparadas del lado del servidor.
    # prepare_threshold=None las desactiva en psycopg 3.
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,  # tras commit() los objetos siguen siendo legibles sin otra consulta
)


@event.listens_for(SessionLocal, "after_begin")
def _apply_rls_context(session: Session, transaction, connection) -> None:
    """Pasa a PostgreSQL el contexto de la petición al iniciar cada transacción."""
    tenant_id = session.info.get("tenant_id")
    if tenant_id:
        connection.execute(text("SELECT set_config('app.tenant_id', :value, true)"), {"value": str(tenant_id)})
    login_email = session.info.get("login_email")
    if login_email:
        connection.execute(text("SELECT set_config('app.login_email', :value, true)"), {"value": login_email})


def get_session() -> Iterator[Session]:
    """Una sesión por petición HTTP; se cierra (y hace rollback si quedó algo) al terminar."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

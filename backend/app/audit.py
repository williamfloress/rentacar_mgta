"""Registro de auditoría: quién hizo qué y cuándo.

record() solo AÑADE la fila a la sesión; se guarda en la MISMA transacción que
la acción auditada. Así, o se guardan ambas o ninguna (no hay acciones sin
rastro ni rastros de acciones que no ocurrieron).
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    user: User,
    action: str,
    entity: str,
    entity_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail,
        )
    )

"""Paginación con total de resultados.

Los listados devuelven una lista JSON (simple de consumir) y el TOTAL de filas
que cumplen el filtro va en la cabecera `X-Total-Count`. Así el frontend puede
mostrar "página 2 de 7" sin una segunda petición y sin envolver la respuesta.
"""

from typing import Annotated

from fastapi import Depends, Query, Response
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

TOTAL_COUNT_HEADER = "X-Total-Count"


class Page:
    def __init__(
        self,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset

    def apply(self, db: Session, stmt: Select, response: Response) -> Select:
        """Cuenta el total del filtro, lo pone en la cabecera y devuelve la consulta paginada.

        El conteo se hace sobre la consulta YA filtrada pero SIN orden ni límite,
        envuelta como subconsulta (funciona igual con joins o condiciones complejas).
        """
        total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        response.headers[TOTAL_COUNT_HEADER] = str(total)
        return stmt.limit(self.limit).offset(self.offset)


PageParams = Annotated[Page, Depends()]

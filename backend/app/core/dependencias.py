"""
Dependencias reutilizables de la API (criterios 34, 35 y 36 de la lista
de chequeo).

Contiene tres piezas que antes estaban repetidas endpoint por endpoint:

1. `ParametrosPaginacion` — dependencia de CLASE, parametrizable: cada
   router la instancia con su propio límite por defecto y su propio
   tope máximo (`Depends(ParametrosPaginacion(limite_por_defecto=10))`).
   Sustituye a copiar cuatro `Query(...)` en cada listado.

2. `obtener_proveedor_o_404` — dependencia ANIDADA (depende a su vez de
   `get_db`) que resuelve el proveedor de la ruta y corta con 404 antes
   de que la función del endpoint llegue a ejecutarse. El endpoint
   recibe el objeto ya cargado y no vuelve a comprobar si existe.

3. `Paginacion` / `ProveedorDeLaRuta` — alias `Annotated` para que la
   firma de cada endpoint quede legible.
"""

from typing import Annotated

from fastapi import Depends, Path, Query
from sqlalchemy.orm import Session

from app.crud import proveedores as crud_proveedores
from app.database import get_db
from app.models.proveedor import Proveedor

LIMITE_POR_DEFECTO = 10
LIMITE_MAXIMO = 50


class PaginacionSolicitada:
    """Resultado ya saneado de `ParametrosPaginacion` (página, límite, offset)."""

    __slots__ = ("pagina", "limite", "offset")

    def __init__(self, pagina: int, limite: int):
        self.pagina = pagina
        self.limite = limite
        self.offset = (pagina - 1) * limite

    def meta(self, total: int) -> dict:
        """Metadatos que acompañan a `datos` en un listado paginado."""
        return {
            "pagina": self.pagina,
            "limite": self.limite,
            "total": total,
            "totalPaginas": 0 if total == 0 else -(-total // self.limite),
        }


class ParametrosPaginacion:
    """
    Dependencia de clase: se configura al construirla y se usa con
    `Depends(...)`.

        paginacion: PaginacionSolicitada = Depends(
            ParametrosPaginacion(limite_por_defecto=20, limite_maximo=100)
        )

    El tope máximo evita que un cliente pida `limit=999999` y arrastre
    la tabla completa en una sola respuesta.
    """

    def __init__(self, limite_por_defecto: int = LIMITE_POR_DEFECTO, limite_maximo: int = LIMITE_MAXIMO):
        self.limite_por_defecto = limite_por_defecto
        self.limite_maximo = limite_maximo

    def __call__(
        self,
        page: Annotated[int, Query(ge=1, description="Número de página (empieza en 1).")] = 1,
        limit: Annotated[int | None, Query(ge=1, description="Elementos por página.")] = None,
    ) -> PaginacionSolicitada:
        limite = min(limit or self.limite_por_defecto, self.limite_maximo)
        return PaginacionSolicitada(pagina=page, limite=limite)


# Alias listo para usar en los endpoints de proveedores.
Paginacion = Annotated[PaginacionSolicitada, Depends(ParametrosPaginacion(limite_por_defecto=10))]


IdProveedor = Annotated[
    int,
    Path(ge=1, description="Identificador numérico del proveedor.", examples=[1]),
]


def obtener_proveedor_o_404(
    proveedor_id: IdProveedor,
    db: Annotated[Session, Depends(get_db)],
) -> Proveedor:
    """
    Dependencia anidada (usa `get_db`) que carga el proveedor de la ruta
    o corta el request con 404 (criterio 35). Se declara una vez y la
    reutilizan GET/PUT/PATCH/DELETE y los sub-recursos, en vez de repetir
    el mismo «si no existe, 404» en seis endpoints.

    `obtener_por_id` lanza `ProveedorNoEncontrado`, que el handler de
    dominio traduce a 404 con el cuerpo de error común.
    """
    return crud_proveedores.obtener_por_id(db, proveedor_id)


ProveedorDeLaRuta = Annotated[Proveedor, Depends(obtener_proveedor_o_404)]

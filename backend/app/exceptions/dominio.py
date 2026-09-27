"""
Jerarquía de excepciones PROPIAS DEL DOMINIO (criterio 28 de la lista
de chequeo).

Por qué existe
--------------
La capa de datos (`app/crud/`) no puede lanzar `HTTPException`: eso
ataría la lógica de negocio al protocolo HTTP y haría imposible
reutilizarla desde un comando de consola, una tarea en segundo plano o
un test unitario (criterio 29). En vez de eso, el CRUD lanza estas
excepciones —que hablan el lenguaje del negocio, no el de HTTP— y los
handlers registrados en `app/core/errores.py` son los únicos que
traducen cada una a su código HTTP (criterio 30).

    capa crud        ->  ProveedorNoEncontrado(...)
    handler          ->  404 {"detail": "...", "error": {...}}

Relación con `app/exceptions/pagos.py`
--------------------------------------
`PagoException` es una jerarquía anterior y paralela, exclusiva de
/api/pagos y /api/webhooks, que responde con el envoltorio
`{"success": false, "error": {...}}` que exige ese módulo. No se toca:
esta jerarquía es la del resto de la API y convive con aquella.
"""

from fastapi import status


class ErrorDeDominio(Exception):
    """
    Raíz de todas las excepciones de negocio de la aplicación.

    Cada subclase declara:
      * `status_code`: el código HTTP con el que el handler responderá.
      * `codigo`: un identificador estable y legible por máquina
        (`PROVEEDOR_NO_ENCONTRADO`) para que el frontend pueda
        reaccionar sin tener que comparar mensajes en español.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    codigo: str = "ERROR_DE_DOMINIO"
    mensaje_por_defecto: str = "No se pudo completar la operación."

    def __init__(self, mensaje: str | None = None, *, campo: str | None = None):
        self.mensaje = mensaje or self.mensaje_por_defecto
        # Campo del recurso al que se refiere el error, cuando aplica
        # (p. ej. "nit" en un conflicto de unicidad). Permite que el
        # formulario del frontend resalte el input exacto.
        self.campo = campo
        super().__init__(self.mensaje)


class RecursoNoEncontrado(ErrorDeDominio):
    """El recurso pedido no existe (o el usuario no puede verlo)."""

    status_code = status.HTTP_404_NOT_FOUND
    codigo = "RECURSO_NO_ENCONTRADO"
    mensaje_por_defecto = "El recurso solicitado no existe."


class ConflictoDeNegocio(ErrorDeDominio):
    """
    La petición es sintácticamente válida pero choca con el estado
    actual del sistema (duplicados, dependencias, transiciones
    imposibles). Responde 409 — nunca 400, 422 ni 500 (criterio 21).
    """

    status_code = status.HTTP_409_CONFLICT
    codigo = "CONFLICTO_DE_NEGOCIO"
    mensaje_por_defecto = "La operación entra en conflicto con el estado actual del recurso."


class ReglaDeNegocioViolada(ErrorDeDominio):
    """
    Los datos son coherentes entre sí pero incumplen una regla del
    dominio que solo el servidor puede evaluar (por ejemplo, un cupo de
    crédito por encima del máximo autorizado para la categoría).
    """

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    codigo = "REGLA_DE_NEGOCIO_VIOLADA"
    mensaje_por_defecto = "La operación incumple una regla de negocio."


# ----------------------------------------------------------------------
# Especializaciones del módulo de proveedores
# ----------------------------------------------------------------------


class ProveedorNoEncontrado(RecursoNoEncontrado):
    codigo = "PROVEEDOR_NO_ENCONTRADO"
    mensaje_por_defecto = "El proveedor solicitado no existe."

    def __init__(self, proveedor_id: int | None = None):
        mensaje = (
            f"No existe un proveedor con id {proveedor_id}."
            if proveedor_id is not None
            else self.mensaje_por_defecto
        )
        super().__init__(mensaje)


class NitDuplicado(ConflictoDeNegocio):
    codigo = "PROVEEDOR_NIT_DUPLICADO"

    def __init__(self, nit: str):
        super().__init__(f"Ya existe un proveedor registrado con el NIT {nit}.", campo="nit")


class ProveedorConProductos(ConflictoDeNegocio):
    """
    Borrar un proveedor que todavía surte productos dejaría filas
    huérfanas en el catálogo: se exige suspenderlo o reasignar sus
    productos primero.
    """

    codigo = "PROVEEDOR_CON_PRODUCTOS"

    def __init__(self, cantidad: int):
        super().__init__(
            f"El proveedor tiene {cantidad} producto(s) asociado(s). "
            "Reasígnalos o suspende el proveedor en lugar de eliminarlo."
        )


class TransicionDeEstadoInvalida(ConflictoDeNegocio):
    """Suspender un proveedor ya suspendido, reactivar uno ya activo, etc."""

    codigo = "PROVEEDOR_TRANSICION_INVALIDA"

    def __init__(self, estado_actual: str, estado_destino: str):
        super().__init__(
            f"No se puede pasar de «{estado_actual}» a «{estado_destino}»: "
            "el proveedor ya se encuentra en ese estado."
        )


# ----------------------------------------------------------------------
# Especializaciones del módulo de productos (recurso principal, criterio 18)
# ----------------------------------------------------------------------


class ProductoNoEncontrado(RecursoNoEncontrado):
    codigo = "PRODUCTO_NO_ENCONTRADO"
    mensaje_por_defecto = "El producto solicitado no existe."

    def __init__(self, producto_id: int | None = None):
        mensaje = (
            f"No existe un producto con id {producto_id}."
            if producto_id is not None
            else self.mensaje_por_defecto
        )
        super().__init__(mensaje)


class SkuDuplicado(ConflictoDeNegocio):
    codigo = "PRODUCTO_SKU_DUPLICADO"

    def __init__(self, sku: str | None = None):
        detalle = f" ({sku})" if sku else ""
        super().__init__(f"Ya existe un producto con ese SKU{detalle}.", campo="sku")


class ProductoConPedidos(ConflictoDeNegocio):
    """
    Borrar un producto que ya tiene pedidos asociados rompería el
    historial de compras (no hay ON DELETE CASCADE en
    `pedido_items.producto_id` a propósito): se exige despublicarlo
    (PATCH /estado) en vez de eliminarlo.
    """

    codigo = "PRODUCTO_CON_PEDIDOS"

    def __init__(self):
        super().__init__(
            "No se puede eliminar un producto que ya tiene pedidos asociados. "
            "Despublícalo en su lugar (PATCH /estado)."
        )

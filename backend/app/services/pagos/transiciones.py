"""
Único punto autorizado para cambiar `Pago.estado` (punto 6 del alcance
del módulo). Nada más en la aplicación debe hacer `pago.estado = X`
directamente.
"""

from app.exceptions.pagos import TransicionEstadoInvalidaException
from app.models.pago import TRANSICIONES_VALIDAS, EstadoPago


def transicionar_estado(estado_actual: EstadoPago, estado_nuevo: EstadoPago) -> EstadoPago:
    """
    Valida y retorna el estado resultante de pasar de `estado_actual` a
    `estado_nuevo`.

    - Si `estado_nuevo == estado_actual`, es un no-op idempotente (el
      mismo evento de Wompi puede llegar duplicado — ver punto 11,
      Idempotencia del webhook — y no debe tratarse como error).
    - Si la transición no está en TRANSICIONES_VALIDAS, se rechaza
      (p. ej. nunca se permite que un pago APPROVED "vuelva" a
      PENDING).
    """
    if estado_actual == estado_nuevo:
        return estado_actual

    permitidos = TRANSICIONES_VALIDAS.get(estado_actual, frozenset())
    if estado_nuevo not in permitidos:
        raise TransicionEstadoInvalidaException(
            f"No se puede pasar un pago de estado '{estado_actual.value}' a '{estado_nuevo.value}'."
        )
    return estado_nuevo

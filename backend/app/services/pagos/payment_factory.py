"""
Factory que elige la implementación de PaymentProvider según el nombre
del proveedor (punto 13 del alcance — Factory/Strategy Pattern).

Agregar MercadoPago/ePayco/PayU/Stripe en el futuro solo requiere:
  1. Crear su <proveedor>_provider.py implementando PaymentProvider.
  2. Agregar una línea al dict `_PROVEEDORES` de abajo.
Sin tocar PaymentService ni los routers.
"""

from app.config import Settings
from app.exceptions.pagos import PagoValidacionException
from app.services.pagos.payment_provider import PaymentProvider
from app.services.pagos.wompi_provider import WompiProvider

_PROVEEDORES = {
    "wompi": WompiProvider,
}


def obtener_proveedor(nombre: str, settings: Settings) -> PaymentProvider:
    clase_proveedor = _PROVEEDORES.get(nombre)
    if clase_proveedor is None:
        raise PagoValidacionException(
            f"Proveedor de pago no soportado: '{nombre}'. Soportados: {', '.join(_PROVEEDORES)}."
        )
    return clase_proveedor(settings)

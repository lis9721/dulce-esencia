"""
Interfaz que debe implementar cualquier proveedor de pago (Wompi hoy;
MercadoPago, ePayco, PayU o Stripe en el futuro — punto 13 del alcance
del módulo), para que PaymentService nunca dependa de un proveedor en
particular.

Un nuevo proveedor solo necesita:
  1. Crear `app/services/pagos/<proveedor>_provider.py` con una clase
     que implemente esta interfaz.
  2. Registrarla en app/services/pagos/payment_factory.py.
Sin tocar PaymentService, los routers, ni los modelos.
"""

from abc import ABC, abstractmethod
from typing import Any


class DatosPagoProveedor:
    """
    Resultado neutral (independiente del proveedor) de crear o
    consultar un pago. `estado` ya viene traducido a EstadoPago del
    proveedor correspondiente por el propio provider.
    """

    def __init__(
        self,
        *,
        id_transaccion_proveedor: str | None,
        estado,
        metodo_pago: str | None = None,
        url_checkout: str | None = None,
        respuesta_cruda: dict[str, Any] | None = None,
        referencia: str | None = None,
    ):
        self.id_transaccion_proveedor = id_transaccion_proveedor
        self.estado = estado
        self.metodo_pago = metodo_pago
        self.url_checkout = url_checkout
        self.respuesta_cruda = respuesta_cruda
        # Solo se usa al extraer un evento de webhook, para poder
        # ubicar el Pago correspondiente por su `referencia` antes de
        # tener a mano `id_transaccion_proveedor` (ver
        # PaymentService.procesar_webhook).
        self.referencia = referencia


class PaymentProvider(ABC):
    @abstractmethod
    def create_payment(
        self,
        *,
        referencia: str,
        monto_centavos: int,
        moneda: str,
        correo_cliente: str,
        nombre_cliente: str | None,
        url_redireccion: str | None,
    ) -> DatosPagoProveedor:
        """Inicia un pago en el proveedor y retorna sus datos iniciales (típicamente PENDING + checkout_url)."""

    @abstractmethod
    def get_payment(self, id_transaccion_proveedor: str) -> DatosPagoProveedor:
        """Consulta el estado actual de una transacción ya existente en el proveedor."""

    @abstractmethod
    def refund_payment(self, id_transaccion_proveedor: str) -> DatosPagoProveedor:
        """Anula/reembolsa una transacción existente."""

    @abstractmethod
    def validate_webhook(self, payload: dict[str, Any]) -> bool:
        """Valida la firma/checksum de un evento de webhook recibido de este proveedor."""

    @abstractmethod
    def extraer_evento_transaccion(self, payload: dict[str, Any]) -> DatosPagoProveedor | None:
        """
        A partir de un payload de webhook YA VALIDADO, extrae los
        datos de la transacción que reporta. Retorna None si el
        evento no es de un tipo relacionado con transacciones (p. ej.
        nequi_token.updated), en cuyo caso el webhook simplemente se
        reconoce (HTTP 200) sin actualizar ningún Pago.
        """

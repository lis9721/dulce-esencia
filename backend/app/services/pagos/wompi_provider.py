"""
Implementación de PaymentProvider para Wompi Colombia.

Usa el flujo de **Web Checkout** de Wompi (formulario/redirección a
https://checkout.wompi.co/p/, ver
https://docs.wompi.co/docs/colombia/widget-checkout-web/) en vez de
crear la transacción directamente vía `POST /transactions`: ese
endpoint exige un `payment_method.token` (un token de tarjeta ya
tokenizada) y un `acceptance_token`, ambos generados en el NAVEGADOR
del cliente con la llave pública — es decir, nunca deben pasar por
este backend. Usar Web Checkout es justamente lo que permite cumplir
el punto 16 del alcance ("la aplicación no debe manejar directamente
datos sensibles de tarjeta"): este backend solo firma un enlace, nunca
ve un número de tarjeta.

Por eso `create_payment` no hace ninguna llamada HTTP a Wompi (no hay
nada que crear todavía del lado de Wompi): solo calcula la firma de
integridad y arma la URL de checkout. La transacción real en Wompi se
crea cuando el cliente completa el pago en esa URL, y este backend se
entera de su `id_transaccion_proveedor` y su estado final por el
webhook (`POST /api/webhooks/wompi`) o por `/sync` (`GET
/transactions/{id}`, una vez ya se conoce el id).
"""

import random
import string
from urllib.parse import urlencode

from app.exceptions.pagos import ProveedorPagoException, WebhookValidacionException
from app.integrations.wompi.client import WompiClient
from app.integrations.wompi.firma import calcular_checksum_evento, generar_firma_integridad
from app.models.pago import EstadoPago
from app.services.pagos.payment_provider import DatosPagoProveedor, PaymentProvider

# Estados que puede devolver Wompi para una transacción (ver
# https://docs.wompi.co/en/docs/colombia/transacciones/, sección
# "Transaction statuses"). EXPIRED es propio de este backend, Wompi
# nunca lo envía.
ESTADOS_WOMPI_VALIDOS = {"PENDING", "APPROVED", "DECLINED", "VOIDED", "ERROR"}


class WompiProvider(PaymentProvider):
    def __init__(self, settings):
        self._settings = settings

    def _validar_credenciales(self, *campos: str) -> None:
        faltantes = [c for c in campos if not getattr(self._settings, c, "")]
        if faltantes:
            raise ProveedorPagoException(
                f"Wompi no está configurado: falta(n) {', '.join(faltantes)} en las variables de entorno."
            )

    def _cliente(self, *, usar_llave_privada: bool = False) -> WompiClient:
        llave = self._settings.WOMPI_PRIVATE_KEY if usar_llave_privada else self._settings.WOMPI_PUBLIC_KEY
        return WompiClient(base_url=self._settings.WOMPI_API_URL, llave_autenticacion=llave)

    @staticmethod
    def _mapear_estado(estado_wompi: str) -> EstadoPago:
        if estado_wompi not in ESTADOS_WOMPI_VALIDOS:
            raise ProveedorPagoException(f"Wompi devolvió un estado de transacción desconocido: '{estado_wompi}'.")
        return EstadoPago(estado_wompi)

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
        self._validar_credenciales("WOMPI_PUBLIC_KEY", "WOMPI_INTEGRITY_SECRET")

        fecha_expiracion = self._calcular_fecha_expiracion()

        firma = generar_firma_integridad(
            referencia=referencia,
            monto_centavos=monto_centavos,
            moneda=moneda,
            secreto_integridad=self._settings.WOMPI_INTEGRITY_SECRET,
            fecha_expiracion=fecha_expiracion,
        )

        parametros = {
            "public-key": self._settings.WOMPI_PUBLIC_KEY,
            "currency": moneda,
            "amount-in-cents": monto_centavos,
            "reference": referencia,
            "signature:integrity": firma,
        }
        if fecha_expiracion:
            parametros["expiration-time"] = fecha_expiracion
        if url_redireccion:
            parametros["redirect-url"] = url_redireccion
        if correo_cliente:
            parametros["customer-data:email"] = correo_cliente
        if nombre_cliente:
            parametros["customer-data:full-name"] = nombre_cliente

        checkout_url = f"{self._settings.WOMPI_CHECKOUT_URL}?{urlencode(parametros)}"

        return DatosPagoProveedor(
            id_transaccion_proveedor=None,
            estado=EstadoPago.PENDING,
            url_checkout=checkout_url,
            respuesta_cruda={"checkout_url": checkout_url, "reference": referencia, "expiration_time": fecha_expiracion},
        )

    def _calcular_fecha_expiracion(self) -> str | None:
        """
        Fecha de vencimiento del link de checkout, en el formato ISO
        8601 UTC con milisegundos que exige Wompi (ver
        https://docs.wompi.co/docs/colombia/widget-checkout-web/,
        ejemplo oficial: "2023-06-09T20:28:50.000Z"). Devuelve None si
        WOMPI_CHECKOUT_EXPIRACION_MINUTOS está en 0 (link sin
        vencimiento del lado de Wompi).
        """
        minutos = self._settings.WOMPI_CHECKOUT_EXPIRACION_MINUTOS
        if not minutos or minutos <= 0:
            return None
        from datetime import datetime, timedelta, timezone

        vencimiento = datetime.now(timezone.utc) + timedelta(minutes=minutos)
        return vencimiento.strftime("%Y-%m-%dT%H:%M:%S.") + f"{vencimiento.microsecond // 1000:03d}Z"

    def get_payment(self, id_transaccion_proveedor: str) -> DatosPagoProveedor:
        self._validar_credenciales("WOMPI_PUBLIC_KEY")
        respuesta = self._cliente().obtener_transaccion(id_transaccion_proveedor)
        transaccion = respuesta.get("data", {})
        return DatosPagoProveedor(
            id_transaccion_proveedor=transaccion.get("id"),
            estado=self._mapear_estado(transaccion.get("status", "")),
            metodo_pago=transaccion.get("payment_method_type"),
            respuesta_cruda=respuesta,
        )

    def refund_payment(self, id_transaccion_proveedor: str) -> DatosPagoProveedor:
        self._validar_credenciales("WOMPI_PRIVATE_KEY")
        respuesta = self._cliente(usar_llave_privada=True).anular_transaccion(id_transaccion_proveedor)
        transaccion = respuesta.get("data", {})
        return DatosPagoProveedor(
            id_transaccion_proveedor=transaccion.get("id", id_transaccion_proveedor),
            estado=self._mapear_estado(transaccion.get("status", "VOIDED")),
            respuesta_cruda=respuesta,
        )

    def validate_webhook(self, payload: dict) -> bool:
        self._validar_credenciales("WOMPI_EVENTS_SECRET")
        try:
            firma = payload["signature"]
            checksum_calculado = calcular_checksum_evento(
                data=payload["data"],
                propiedades=firma["properties"],
                timestamp=payload["timestamp"],
                secreto_eventos=self._settings.WOMPI_EVENTS_SECRET,
            )
        except (KeyError, TypeError) as error:
            raise WebhookValidacionException("El evento de Wompi no tiene la estructura esperada.") from error

        checksum_recibido = str(firma.get("checksum", "")).lower()
        return checksum_calculado.lower() == checksum_recibido

    def extraer_evento_transaccion(self, payload: dict) -> DatosPagoProveedor | None:
        if payload.get("event") != "transaction.updated":
            return None

        transaccion = payload.get("data", {}).get("transaction")
        if not transaccion:
            return None

        return DatosPagoProveedor(
            id_transaccion_proveedor=transaccion.get("id"),
            estado=self._mapear_estado(transaccion.get("status", "")),
            metodo_pago=transaccion.get("payment_method_type"),
            referencia=transaccion.get("reference"),
            respuesta_cruda=None,
        )


def generar_referencia() -> str:
    """
    Referencia única de pago, formato ESSENTIA-YYYYMMDD-XXXXXXXX (igual
    al ejemplo del punto 7 del alcance). El sufijo alfanumérico
    aleatorio evita colisiones entre pagos creados el mismo día.
    """
    from datetime import datetime, timezone

    fecha = datetime.now(timezone.utc).strftime("%Y%m%d")
    sufijo = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"ESSENTIA-{fecha}-{sufijo}"

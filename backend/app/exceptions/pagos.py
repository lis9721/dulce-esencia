"""
Excepciones propias del módulo de pagos y sus exception handlers de
FastAPI.

El resto de esta API (app/routes/pedidos.py, productos.py, etc.) usa
HTTPException directamente y responde `{"detail": "..."}`. El módulo
de pagos usa este formato más estructurado en su lugar:

    {"success": false, "error": {"code": "...", "message": "..."}}

porque así lo pide explícitamente el punto 15 del alcance del módulo
(útil para que un frontend distinga por código de error, no solo por
mensaje). Es un formato adicional, exclusivo de /api/pagos y
/api/webhooks — no reemplaza el manejo de errores del resto de la
aplicación.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class PagoException(Exception):
    """Excepción base del módulo de pagos."""

    codigo = "PAYMENT_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, mensaje: str):
        self.mensaje = mensaje
        super().__init__(mensaje)


class PagoNoEncontradoException(PagoException):
    codigo = "PAYMENT_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class PagoValidacionException(PagoException):
    codigo = "PAYMENT_VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class ProveedorPagoException(PagoException):
    """Error al comunicarse con el proveedor de pago (Wompi u otro)."""

    codigo = "PAYMENT_PROVIDER_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY


class WebhookValidacionException(PagoException):
    """Firma/checksum de un webhook inválida — nunca debe procesarse."""

    codigo = "WEBHOOK_VALIDATION_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST


class TransicionEstadoInvalidaException(PagoException):
    codigo = "PAYMENT_INVALID_STATE_TRANSITION"
    status_code = status.HTTP_409_CONFLICT


def manejador_pago_exception(request: Request, exc: PagoException) -> JSONResponse:
    """
    Handler genérico para toda la jerarquía de PagoException. Nunca
    incluye stack traces ni datos sensibles (ver punto 15: "No exponer
    stack traces ni secretos en producción") — solo el código y el
    mensaje ya pensado para el usuario final que arma cada excepción.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.codigo, "message": exc.mensaje}},
    )


def registrar_manejadores_excepciones(app) -> None:
    """Se llama una vez desde app/main.py para registrar todos los handlers de este módulo."""
    app.add_exception_handler(PagoException, manejador_pago_exception)

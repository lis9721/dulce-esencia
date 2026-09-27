"""
Cliente HTTP hacia la API de Wompi (`WOMPI_API_URL`, por defecto
https://sandbox.wompi.co/v1 en sandbox).

Usa httpx.Client (SÍNCRONO) en vez de httpx.AsyncClient a propósito:
todo este backend es síncrono (SQLAlchemy Session normal, rutas
`def` no `async def` — ver app/routes/pedidos.py, auth.py, etc., y
app/database.py que usa `create_engine` en vez de
`create_async_engine`). Mezclar un cliente async dentro de rutas sync
obligaría a levantar un event loop nuevo en cada llamada (o volver
async media aplicación), así que este cliente sigue la misma
convención síncrona que ya usa el resto del proyecto.

Implementa timeout, reintentos controlados para errores transitorios
(5xx / timeouts de red — nunca para 4xx, que son errores del cliente
que no se arreglan reintentando) y logging sin datos sensibles (nunca
se registran las llaves de Wompi ni el cuerpo completo de la
respuesta).
"""

import logging
import time

import httpx

from app.exceptions.pagos import ProveedorPagoException

logger = logging.getLogger("app.integrations.wompi")

MAX_INTENTOS = 3
ESPERA_BASE_SEGUNDOS = 0.5
TIMEOUT_SEGUNDOS = 10.0


class WompiClient:
    """Envoltorio delgado sobre httpx.Client para GET/POST hacia la API de Wompi."""

    def __init__(self, base_url: str, llave_autenticacion: str):
        self._base_url = base_url.rstrip("/")
        self._llave = llave_autenticacion

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._llave}",
            "Content-Type": "application/json",
        }

    def _solicitar(self, metodo: str, ruta: str, **kwargs) -> dict:
        url = f"{self._base_url}{ruta}"
        ultimo_error: Exception | None = None

        for intento in range(1, MAX_INTENTOS + 1):
            inicio = time.monotonic()
            try:
                with httpx.Client(timeout=TIMEOUT_SEGUNDOS) as cliente:
                    respuesta = cliente.request(metodo, url, headers=self._headers(), **kwargs)
                duracion_ms = round((time.monotonic() - inicio) * 1000, 1)

                # Solo se registran metadatos de la llamada, nunca las
                # llaves (self._llave) ni el cuerpo de la petición/respuesta.
                logger.info(
                    "wompi_request",
                    extra={"metodo": metodo, "ruta": ruta, "status": respuesta.status_code, "duracion_ms": duracion_ms},
                )

                if respuesta.status_code >= 500 and intento < MAX_INTENTOS:
                    ultimo_error = ProveedorPagoException(f"Wompi respondió {respuesta.status_code}, reintentando.")
                    time.sleep(ESPERA_BASE_SEGUNDOS * intento)
                    continue

                if respuesta.status_code >= 400:
                    raise ProveedorPagoException(
                        f"Wompi respondió {respuesta.status_code} para {metodo} {ruta}."
                    )

                return respuesta.json()

            except httpx.TimeoutException as error:
                ultimo_error = error
                logger.warning("wompi_timeout", extra={"metodo": metodo, "ruta": ruta, "intento": intento})
                if intento < MAX_INTENTOS:
                    time.sleep(ESPERA_BASE_SEGUNDOS * intento)
                    continue
            except httpx.HTTPError as error:
                ultimo_error = error
                logger.warning("wompi_http_error", extra={"metodo": metodo, "ruta": ruta, "intento": intento})
                if intento < MAX_INTENTOS:
                    time.sleep(ESPERA_BASE_SEGUNDOS * intento)
                    continue

        raise ProveedorPagoException(f"No fue posible comunicarse con Wompi ({metodo} {ruta}).") from ultimo_error

    def obtener_transaccion(self, id_transaccion: str) -> dict:
        """GET /transactions/{id} — consulta el estado actual de una transacción."""
        return self._solicitar("GET", f"/transactions/{id_transaccion}")

    def anular_transaccion(self, id_transaccion: str) -> dict:
        """POST /transactions/{id}/void — anula una transacción con tarjeta. Requiere llave privada."""
        return self._solicitar("POST", f"/transactions/{id_transaccion}/void")

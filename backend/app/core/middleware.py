"""
Middlewares propios de la aplicación (criterio 45 de la lista de
chequeo): registro de peticiones y cabeceras de seguridad.

Reemplazan en Python lo que en el backend Node hacían `morgan` (log de
accesos) y `helmet` (cabeceras). Se registran en app/main.py.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("app.acceso")

# Cabeceras de seguridad. Equivalen al subconjunto de `helmet` que tiene
# sentido para una API JSON servida a un SPA:
#   * nosniff           — el navegador no adivina el tipo de contenido.
#   * DENY              — la API no puede embeberse en un <iframe> ajeno
#                         (defensa contra clickjacking).
#   * no-referrer       — la URL de la API nunca viaja como Referer.
#   * Permissions-Policy— se apagan cámara, micrófono y geolocalización,
#                         que esta API nunca necesita.
#   * CSP restrictiva   — las respuestas son JSON; nada debe ejecutarse.
# HSTS se agrega solo en producción (ver `solo_https`): forzarlo en
# desarrollo dejaría el navegador "pegado" a https://localhost.
CABECERAS_SEGURIDAD = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    "Cross-Origin-Resource-Policy": "same-site",
}

# Rutas de documentación (Swagger UI y ReDoc): son HTML que carga CSS y
# JS desde un CDN, así que la CSP de arriba las dejaría en blanco. Se
# excluyen de esa cabecera puntual (las demás sí aplican).
RUTAS_DOCUMENTACION = ("/docs", "/redoc", "/openapi.json")


class CabecerasSeguridadMiddleware(BaseHTTPMiddleware):
    """Agrega las cabeceras de seguridad a TODAS las respuestas."""

    def __init__(self, app: ASGIApp, solo_https: bool = False):
        super().__init__(app)
        self.solo_https = solo_https

    async def dispatch(self, request, call_next):
        respuesta = await call_next(request)
        es_documentacion = request.url.path.startswith(RUTAS_DOCUMENTACION)

        for nombre, valor in CABECERAS_SEGURIDAD.items():
            if es_documentacion and nombre in {"Content-Security-Policy", "Cross-Origin-Resource-Policy"}:
                continue
            respuesta.headers.setdefault(nombre, valor)

        if self.solo_https:
            respuesta.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return respuesta


class RegistroPeticionesMiddleware(BaseHTTPMiddleware):
    """
    Registra una línea por petición con método, ruta, código y duración,
    y agrega un `X-Request-ID` que permite correlacionar un error visto
    por el usuario con su traza exacta en el log del servidor.

    Nunca registra el cuerpo de la petición ni la cabecera
    Authorization: ahí viajan contraseñas y tokens.
    """

    async def dispatch(self, request, call_next):
        id_peticion = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.id_peticion = id_peticion
        inicio = time.perf_counter()

        try:
            respuesta = await call_next(request)
        except Exception:
            duracion_ms = (time.perf_counter() - inicio) * 1000
            logger.exception(
                "peticion_fallida id=%s metodo=%s ruta=%s duracion_ms=%.1f",
                id_peticion,
                request.method,
                request.url.path,
                duracion_ms,
            )
            # Se re-lanza para que el handler de 500 (app/core/errores.py)
            # arme la respuesta con el formato común.
            raise

        duracion_ms = (time.perf_counter() - inicio) * 1000
        logger.info(
            "peticion id=%s metodo=%s ruta=%s estado=%s duracion_ms=%.1f",
            id_peticion,
            request.method,
            request.url.path,
            respuesta.status_code,
            duracion_ms,
        )
        respuesta.headers["X-Request-ID"] = id_peticion
        return respuesta

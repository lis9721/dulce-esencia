"""
Formato ÚNICO de error para toda la API y los handlers que lo producen
(criterios 30, 31, 32 y 33 de la lista de chequeo).

El cuerpo de error
------------------
Cualquier error —404, 409, 422 de Pydantic o un 500 inesperado— sale
siempre con esta misma forma:

    {
      "detail": "Mensaje legible para la persona",
      "error": {
        "codigo": "PROVEEDOR_NIT_DUPLICADO",
        "mensaje": "Ya existe un proveedor registrado con el NIT 900123456-7.",
        "campos": [ {"campo": "nit", "mensaje": "..."} ],   // vacío si no aplica
        "ruta": "/api/proveedores"
      }
    }

`detail` se mantiene (con el mismo contenido que antes de este cambio:
texto en los errores normales y la lista de Pydantic en los 422) para
no romper a ningún cliente ya escrito contra la API —incluido este
mismo frontend— mientras que `error` agrega la parte estructurada:
código estable, mensaje y detalle campo por campo.

Excepción deliberada: /api/pagos y /api/webhooks conservan su propio
envoltorio `{"success": false, "error": {"code", "message"}}`, exigido
por el alcance del módulo de pagos (ver app/exceptions/pagos.py).

Un 500 nunca revela nada
------------------------
`manejador_error_inesperado` responde un mensaje genérico y registra la
traza completa con `logger.exception` (criterio 33): el detalle técnico
queda en el log del servidor, nunca en la respuesta HTTP.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.dominio import ErrorDeDominio

logger = logging.getLogger("app.errores")

# Prefijos que conservan el formato propio del módulo de pagos.
PREFIJOS_FORMATO_PAGOS = ("/api/pagos", "/api/webhooks")

# Código genérico por status para los HTTPException que se siguen
# lanzando a mano en los routers antiguos (usuarios, productos, ...):
# así incluso esos errores traen un `codigo` estable.
CODIGOS_POR_STATUS = {
    status.HTTP_400_BAD_REQUEST: "PETICION_INVALIDA",
    status.HTTP_401_UNAUTHORIZED: "NO_AUTENTICADO",
    status.HTTP_403_FORBIDDEN: "SIN_PERMISO",
    status.HTTP_404_NOT_FOUND: "RECURSO_NO_ENCONTRADO",
    status.HTTP_409_CONFLICT: "CONFLICTO_DE_NEGOCIO",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDACION_FALLIDA",
    status.HTTP_429_TOO_MANY_REQUESTS: "DEMASIADAS_PETICIONES",
    status.HTTP_502_BAD_GATEWAY: "PROVEEDOR_EXTERNO_NO_DISPONIBLE",
}


def _usa_formato_de_pagos(request: Request) -> bool:
    return request.url.path.startswith(PREFIJOS_FORMATO_PAGOS)


def construir_cuerpo_error(
    *,
    ruta: str,
    codigo: str,
    mensaje: str,
    detail=None,
    campos: list[dict] | None = None,
) -> dict:
    """Única función que arma un cuerpo de error en toda la aplicación."""
    return {
        "detail": detail if detail is not None else mensaje,
        "error": {
            "codigo": codigo,
            "mensaje": mensaje,
            "campos": campos or [],
            "ruta": ruta,
        },
    }


def manejador_error_de_dominio(request: Request, exc: ErrorDeDominio) -> JSONResponse:
    """
    Traduce CADA excepción de la jerarquía de dominio a su código HTTP
    (criterio 30). El mapeo vive en la propia excepción (`status_code`),
    no en una cadena de `if` aquí: agregar una excepción nueva no obliga
    a tocar este archivo.
    """
    campos = [{"campo": exc.campo, "mensaje": exc.mensaje}] if exc.campo else []
    return JSONResponse(
        status_code=exc.status_code,
        content=construir_cuerpo_error(
            ruta=request.url.path,
            codigo=exc.codigo,
            mensaje=exc.mensaje,
            campos=campos,
        ),
    )


def manejador_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Los `HTTPException` que todavía se lanzan a mano en los routers
    anteriores (usuarios, productos, pedidos...) también salen con el
    formato común, sin tener que reescribir cada router.
    """
    mensaje = exc.detail if isinstance(exc.detail, str) else "La petición no pudo completarse."
    cuerpo = construir_cuerpo_error(
        ruta=request.url.path,
        codigo=CODIGOS_POR_STATUS.get(exc.status_code, "ERROR_HTTP"),
        mensaje=mensaje,
        detail=exc.detail,
    )
    # Cabeceras propias del error (WWW-Authenticate en los 401, ver
    # app/auth.py — criterio 42): se conservan tal cual.
    return JSONResponse(status_code=exc.status_code, content=cuerpo, headers=getattr(exc, "headers", None))


def manejador_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    422 de Pydantic con el MISMO envoltorio que el resto (criterio 32) y
    con el detalle campo por campo ya resuelto: el frontend no tiene que
    interpretar la estructura `loc` de Pydantic para saber qué input
    marcar en rojo.
    """
    campos = []
    for error in exc.errors():
        # loc = ("body", "nit") -> se descarta el primer elemento
        # ("body"/"query"/"path"), que no es un nombre de campo.
        partes = [str(parte) for parte in error.get("loc", []) if str(parte) not in {"body", "query", "path"}]
        campos.append(
            {
                "campo": ".".join(partes) or "cuerpo",
                "mensaje": error.get("msg", "Valor inválido."),
            }
        )

    # exc.errors() no siempre es serializable en JSON tal cual: cuando un
    # @field_validator propio levanta ValueError (como en
    # ChatbotMensajeEntrada._valida_mensaje, o en los ~90 validadores del
    # resto de esquemas), Pydantic guarda esa excepción sin convertir en
    # error["ctx"]["error"]. json.dumps no sabe serializar un ValueError y
    # el 422 terminaba reventando como 500 (bug real: ver
    # test_mensaje_vacio_422). jsonable_encoder con un default a str()
    # cubre ese caso y cualquier otro objeto no serializable que aparezca
    # en "ctx".
    detalle_serializable = jsonable_encoder(exc.errors(), custom_encoder={Exception: str})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=construir_cuerpo_error(
            ruta=request.url.path,
            codigo="VALIDACION_FALLIDA",
            mensaje="Hay campos inválidos en la petición.",
            # Se conserva la lista cruda de Pydantic en `detail` para no
            # romper clientes que ya la leían así.
            detail=detalle_serializable,
            campos=campos,
        ),
    )


def manejador_error_inesperado(request: Request, exc: Exception) -> JSONResponse:
    """
    Red de seguridad: cualquier excepción no prevista responde 500 con un
    mensaje genérico y deja la traza completa en el log (criterio 33).
    """
    logger.exception("error_inesperado metodo=%s ruta=%s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=construir_cuerpo_error(
            ruta=request.url.path,
            codigo="ERROR_INTERNO",
            mensaje="Ocurrió un error inesperado en el servidor. El equipo ya fue notificado.",
        ),
    )


def registrar_manejadores_globales(app: FastAPI) -> None:
    """Se llama una sola vez desde app/main.py."""

    @app.exception_handler(ErrorDeDominio)
    async def _dominio(request: Request, exc: ErrorDeDominio):
        return manejador_error_de_dominio(request, exc)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        if _usa_formato_de_pagos(request):
            # El módulo de pagos mantiene su propio envoltorio.
            return JSONResponse(
                status_code=exc.status_code,
                content={"success": False, "error": {"code": "HTTP_ERROR", "message": exc.detail}},
                headers=getattr(exc, "headers", None),
            )
        return manejador_http_exception(request, exc)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        return manejador_validacion(request, exc)

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception):
        return manejador_error_inesperado(request, exc)

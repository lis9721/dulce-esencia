"""
Rate limiting — equivalente en Python a
backend-node/middlewares/rateLimit.middleware.js.

Node usa express-rate-limit con tres limitadores distintos (login,
registro, recuperar). Este módulo replica exactamente las mismas
ventanas de tiempo, los mismos topes de intentos y los mismos mensajes,
usando slowapi (que envuelve limits.py) sobre la IP remota.

No estaba en el requirements.txt original de este backend — ver
"slowapi" agregado ahí. Antes de este cambio, nada frenaba fuerza bruta
contra /api/auth/login ni contra la creación masiva de cuentas o el
spam de /recuperar.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Mismo criterio que limiterLogin en Node: 10 intentos por IP cada 15
# minutos. Cuenta también los intentos fallidos, que es lo que importa
# para frenar credential stuffing.
LIMITE_LOGIN = "10/15minutes"
MENSAJE_LIMITE_LOGIN = "Demasiados intentos de inicio de sesión. Intenta de nuevo en unos minutos."

# Mismo criterio que limiterRegistro en Node: más permisivo que login
# porque un usuario legítimo puede equivocarse varias veces llenando el
# formulario, pero igual evita que un script cree cientos de cuentas.
LIMITE_REGISTRO = "20/hour"
MENSAJE_LIMITE_REGISTRO = "Demasiadas cuentas creadas desde esta conexión. Intenta más tarde."

# Mismo criterio que limiterRecuperar en Node: se usa en /recuperar,
# /restablecer y /reenviar-verificacion, para no poder usarse para
# saturar la bandeja de entrada de un correo real ni la BD.
LIMITE_RECUPERAR = "5/15minutes"
MENSAJE_LIMITE_RECUPERAR = "Demasiadas solicitudes de recuperación. Intenta de nuevo en unos minutos."

# Mismo criterio que limiterCupon en Node: más permisivo que login
# porque un cliente real puede tipear mal el código un par de veces
# mientras compra, pero igual evita fuerza bruta de códigos
# (VERANO01, VERANO02, ... hasta acertar uno vigente).
LIMITE_CUPON = "30/15minutes"
MENSAJE_LIMITE_CUPON = "Demasiados intentos con códigos de cupón. Intenta de nuevo en unos minutos."


def manejador_limite_excedido(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Reemplaza el handler por defecto de slowapi (que responde
    {"error": "..."}) por uno que responde {"detail": "..."}, para que
    un 429 tenga el mismo shape que cualquier otro error de esta API
    (ver extraerMensajeError en el frontend) — y con el mensaje en
    español propio de cada ruta (pasado vía error_message= en cada
    @limiter.limit(...), no el genérico de slowapi).
    """
    respuesta = JSONResponse({"detail": exc.detail}, status_code=429)
    return request.app.state.limiter._inject_headers(respuesta, request.state.view_rate_limit)

"""
Utilidades de autenticación compartidas entre las rutas (app/routes/).

Equivalente en Python a backend-node/middlewares/auth.middleware.js
(verificación de JWT/roles) y al uso de bcrypt en
backend-node/routes/usuarios.routes.js.

Usa las variables propias de este backend (SECRET_KEY, ALGORITHM,
ACCESS_TOKEN_EXPIRE_MINUTES del .env), no las del backend Node.

--------------------------------------------------------------------
Decisión de arquitectura: Bearer como mecanismo PRINCIPAL de sesión
--------------------------------------------------------------------
El backend Node (backend-node/middlewares/auth.middleware.js) usa la
cookie httpOnly como fuente principal del JWT y el header
"Authorization: Bearer <token>" solo como fallback para Postman.

Este backend Python invierte esa prioridad a propósito: el header
Authorization: Bearer <token> es el mecanismo PRINCIPAL (no un
fallback), porque:
  1. Es lo que el enunciado del cuarto avance pide explícitamente
     ("Authorization: Bearer TOKEN", punto 11).
  2. Es lo que se prueba y evidencia en Swagger UI / Postman (puntos
     25-26 del enunciado) — Swagger no puede fabricar cookies
     httpOnly por sí solo, pero sí tiene un campo nativo para pegar un
     Bearer token vía HTTPBearer.
No se implementa autenticación por cookie en este backend. Si más
adelante se quiere volver a esa opción (mejor protegida contra XSS
para el frontend real), se puede agregar como fuente adicional sin
tocar esta decisión de fondo.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.usuario import Usuario
from app.repositories.usuario_repository import buscar_por_correo

settings = get_settings()

# auto_error=False: si no hay header, lo manejamos nosotros mismos en
# get_current_user() para poder dar el mismo mensaje/código que Node,
# en vez del genérico que da FastAPI por defecto.
bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description='Token JWT obtenido en POST /api/auth/login. Enviar como "Authorization: Bearer &lt;token&gt;".',
    auto_error=False,
)


def crear_hash(password: str) -> str:
    """
    Genera el hash bcrypt de una contraseña en texto plano, usando
    passlib.hash.bcrypt (equivalente a bcrypt.hash() en Node).
    """
    return bcrypt.hash(password)


def verificar_hash(password: str, hash: str) -> bool:
    """
    Compara una contraseña en texto plano contra su hash bcrypt,
    usando passlib.hash.bcrypt (equivalente a bcrypt.compare() en Node).
    """
    return bcrypt.verify(password, hash)


def crear_access_token(datos: dict, expira: timedelta | None = None) -> str:
    """
    Firma un JWT con python-jose. `datos` debe incluir al menos "sub"
    (correo del usuario) y "role" (rol del usuario), igual al ejemplo
    conceptual del PDF del cuarto avance:

        {"sub": "usuario@correo.com", "role": "cliente", "exp": ...}

    Si no se indica `expira`, usa ACCESS_TOKEN_EXPIRE_MINUTES del .env.
    """
    a_codificar = datos.copy()
    momento_expira = datetime.now(timezone.utc) + (
        expira or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    a_codificar["exp"] = momento_expira
    return jwt.encode(a_codificar, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_access_token(token: str) -> dict | None:
    """
    Verifica firma y expiración de un JWT y retorna su payload
    ({"sub": ..., "role": ..., "exp": ...}), o None si es inválido o
    expiró.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Dependencia de FastAPI que protege un endpoint exigiendo un JWT
    válido en el header "Authorization: Bearer <token>" (ver decisión
    de arquitectura arriba).

    Equivalente a verificarToken() en
    backend-node/middlewares/auth.middleware.js, incluyendo sus dos
    partes más importantes:
      - El rol y el estado `activo` del usuario NUNCA se toman del
        payload del token — se vuelven a consultar en la BD en cada
        petición. Así, si un admin desactiva (o cambia el rol de) esta
        cuenta, el corte de acceso aplica de inmediato en la siguiente
        petición, sin esperar a que el JWT viejo expire (hasta
        ACCESS_TOKEN_EXPIRE_MINUTES después).
      - `token_version` ("tv" en el payload) se compara contra la BD:
        si no coincide, el JWT se rechaza aunque su firma y expiración
        sigan siendo válidas. Ver el incremento de `token_version` en
        cambiar_password() y restablecer_password() en routes/usuarios.py.
    """
    error_sin_token = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se proporcionó un token. Inicia sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciales is None or not credenciales.credentials:
        raise error_sin_token

    payload = decodificar_access_token(credenciales.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token expiró o es inválido. Inicia sesión de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    correo = payload.get("sub")
    if not correo:
        raise error_sin_token

    error_token_revocado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tu sesión ya no es válida (se cambió la contraseña o se cerró sesión en todos los dispositivos). Inicia sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # SIEMPRE se relee de la BD — nunca se confía en lo que decía el
    # token en el momento del login (mismo comentario que arriba).
    usuario = buscar_por_correo(db, correo)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tu cuenta ya no existe. Inicia sesión de nuevo.",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está inactiva. Contacta a un administrador de Dulce Esencia.",
        )

    # "tv" (token_version) es el mecanismo real de revocación de JWTs:
    # como el JWT en sí no puede "borrarse" del lado del servidor antes
    # de que expire, cambiar la contraseña (o restablecerla) incrementa
    # usuarios.token_version — cualquier JWT firmado ANTES de ese
    # incremento (con un "tv" más viejo) deja de servir de inmediato,
    # sin esperar ACCESS_TOKEN_EXPIRE_MINUTES. Los JWTs previos a este
    # cambio no traen "tv" en absoluto; se tratan como versión 0, igual
    # que el valor por defecto de la columna en la BD.
    if payload.get("tv", 0) != usuario.token_version:
        raise error_token_revocado

    return usuario


def get_current_user_opcional(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario | None:
    """
    Variante de get_current_user() que NO exige sesión: si no hay
    token (o es inválido/expirado), devuelve None en vez de lanzar
    401. Pensada para endpoints públicos que se comportan distinto si
    hay sesión (ej. POST /api/chatbot/mensaje: un invitado puede
    chatear igual, pero si está logueado la conversación queda
    asociada a su cuenta).
    """
    if credenciales is None or not credenciales.credentials:
        return None
    try:
        return get_current_user(credenciales, db)
    except HTTPException:
        return None


def requiere_rol(*roles_permitidos: str):
    """
    Dependencia factory equivalente a verificarRol(...) en Node. Úsala
    DESPUÉS de get_current_user:

        @router.post("/", dependencies=[Depends(requiere_rol("admin"))])

    o, si necesitas el usuario en el cuerpo de la función:

        def crear(usuario: Usuario = Depends(requiere_rol("admin"))): ...

    El rol viene de `usuario.rol` (ya releído de la BD por
    get_current_user, nunca del payload del token).
    """

    def verificador(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción.",
            )
        return usuario

    return verificador

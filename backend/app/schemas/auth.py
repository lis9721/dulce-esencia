"""
Esquemas Pydantic de entrada/salida para /api/auth.
"""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.usuario import UsuarioSalida

# Un código OTP es SIEMPRE 6 dígitos numéricos (ver generar_otp() en
# routes/usuarios.py). Cualquier otra forma (más corto, con letras, con
# espacios) es inválida de entrada — ni vale la pena tocar la base de
# datos para comprobarlo, FastAPI responde 422 antes de eso.
REGEX_CODIGO_OTP = re.compile(r"^\d{6}$")


def _validar_codigo_otp(v: str) -> str:
    valor = (v or "").strip()
    if not valor:
        raise ValueError("El código es obligatorio.")
    if not REGEX_CODIGO_OTP.match(valor):
        raise ValueError("El código debe tener exactamente 6 dígitos numéricos.")
    return valor

# bcrypt.compare (ver app/auth.py:verificar_hash) ignora en silencio
# todo lo que exceda 72 BYTES de la entrada — mismo límite que en el
# registro (ver schemas/usuario.py), pero aquí SIN exigir complejidad:
# una cuenta antigua pudo crearse con reglas distintas a las actuales,
# así que el login solo valida formato/largo (réplica de
# validarPasswordLogin() en backend-node/utils/validadores.js).
MAX_BYTES_PASSWORD = 72


class LoginEntrada(BaseModel):
    """Body de POST /api/auth/login."""

    model_config = ConfigDict(str_strip_whitespace=True, json_schema_extra={"examples": [{"correo": "cliente@ejemplo.com", "password": "MiClave2026!"}]})

    correo: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def _valida_password(cls, v: str) -> str:
        valor = v or ""
        if not valor:
            raise ValueError("La contraseña es obligatoria.")
        if len(valor) < 8:
            raise ValueError("Debe tener al menos 8 caracteres.")
        if len(valor.encode("utf-8")) > MAX_BYTES_PASSWORD:
            raise ValueError(f"La contraseña es demasiado larga (máximo {MAX_BYTES_PASSWORD} bytes en UTF-8).")
        return valor


class TokenSalida(BaseModel):
    """
    Respuesta de POST /api/auth/login. `token_type` sigue el estándar
    OAuth2/JWT ("bearer") que espera el header
    "Authorization: Bearer <access_token>" (ver decisión de
    arquitectura en app/auth.py: Bearer es el mecanismo principal de
    sesión en este backend, no un fallback).
    """

    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioSalida


class RecuperarEntrada(BaseModel):
    """Body de POST /api/usuarios/recuperar. Réplica de la validación
    mínima de Node (solo exige que el correo esté presente y tenga
    formato válido; ver routes/usuarios.py sobre por qué la respuesta
    es siempre genérica sin importar si el correo existe)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    correo: EmailStr


class ReenviarVerificacionEntrada(BaseModel):
    """Body de POST /api/usuarios/reenviar-verificacion. Misma forma
    que RecuperarEntrada — solo el correo."""

    model_config = ConfigDict(str_strip_whitespace=True)

    correo: EmailStr


class VerificarCorreoEntrada(BaseModel):
    """
    Body de POST /api/usuarios/verificar-correo (segundo paso del
    registro): mismo par correo+código que RestablecerEntrada, pero sin
    contraseña — esta ruta solo confirma la cuenta, no la modifica.
    `codigo` es el OTP de 6 dígitos que se envió por correo (ver
    generar_otp() en routes/usuarios.py).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    correo: EmailStr
    codigo: str

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str) -> str:
        return _validar_codigo_otp(v)


class RestablecerEntrada(BaseModel):
    """
    Body de POST /api/usuarios/restablecer. `codigo` es el OTP de 6
    dígitos enviado por POST /recuperar. `password_nueva` usa la misma
    regla de complejidad que en el registro (validarPassword() en
    Node), a diferencia de LoginEntrada.password que solo valida
    formato — aquí SÍ se está fijando una contraseña nueva.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    correo: EmailStr
    codigo: str
    password_nueva: str

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str) -> str:
        return _validar_codigo_otp(v)

    @field_validator("password_nueva")
    @classmethod
    def _valida_password_nueva(cls, v: str) -> str:
        from app.schemas.usuario import validar_password_nueva

        return validar_password_nueva(v)

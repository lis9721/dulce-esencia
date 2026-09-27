"""
Esquemas Pydantic de entrada/salida para /api/usuarios.

Réplica en Pydantic de las reglas que ya vivían en
backend-node/utils/validadores.js (fuente de verdad original), para
que un mismo dato sea rechazado con el mismo criterio sin importar
qué backend (Node o este, Python) lo reciba. Cada validador de campo
enlaza en su docstring la función equivalente de validadores.js.

Estos esquemas NO tocan la base de datos ni el hasheo de contraseñas
(eso sigue en app/auth.py) — solo definen la forma y las reglas de
validación de lo que entra y sale por la API.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.usuario import RolUsuario, TipoDocumento

REGEX_SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÑÜáéíóúñü\s]+$")
REGEX_SOLO_NUMEROS = re.compile(r"^[0-9]+$")

# bcrypt (ver app/auth.py:crear_hash) ignora en silencio todo lo que
# exceda 72 BYTES de la entrada. Se valida ANTES de hashear para no
# dejar que trunque en silencio. Se mide en bytes UTF-8, no en
# caracteres, por la misma razón que en validadores.js: un emoji o una
# tilde puede ocupar más de 1 byte.
MAX_BYTES_PASSWORD = 72


def validar_nombre_propio(valor: str) -> str:
    """
    Regla de validarNombre()/validarNombreConLargoMaximo() en
    validadores.js, aplicada a `nombre` y `apellido`
    (usuarios.nombre/apellido son VARCHAR(40), acotados a 30 por UX).
    """
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("Este campo es obligatorio.")
    if len(valor) < 2:
        raise ValueError("Debe tener al menos 2 caracteres.")
    if len(valor) > 30:
        raise ValueError("Debe tener máximo 30 caracteres.")
    if not REGEX_SOLO_LETRAS.match(valor):
        raise ValueError("Solo se permiten letras y espacios.")
    return valor


def validar_documento(valor: str) -> str:
    """Regla de validarDocumento() en validadores.js."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("El número de documento es obligatorio.")
    if not REGEX_SOLO_NUMEROS.match(valor):
        raise ValueError("El documento solo debe contener números.")
    if len(valor) < 5 or len(valor) > 15:
        raise ValueError("Debe tener entre 5 y 15 dígitos.")
    return valor


def validar_direccion(valor: str) -> str:
    """Regla de validarDireccion() en validadores.js."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("La dirección es obligatoria.")
    if len(valor) < 5:
        raise ValueError("Debe tener al menos 5 caracteres.")
    if len(valor) > 80:
        raise ValueError("Debe tener máximo 80 caracteres.")
    return valor


def validar_telefono(valor: str) -> str:
    """Regla de validarTelefono() en validadores.js."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("El teléfono es obligatorio.")
    if not REGEX_SOLO_NUMEROS.match(valor):
        raise ValueError("El teléfono solo debe contener números.")
    if len(valor) < 7 or len(valor) > 15:
        raise ValueError("Debe tener entre 7 y 15 dígitos.")
    return valor


def validar_correo_largo(valor: str) -> str:
    """
    Complemento a EmailStr (que ya exige el formato): réplica del
    tope de longitud de validarCorreo() en validadores.js
    (usuarios.correo es VARCHAR(60)).
    """
    if len(valor) > 60:
        raise ValueError("Debe tener máximo 60 caracteres.")
    return valor


def validar_password_nueva(valor: str) -> str:
    """
    Regla de validarPassword() en validadores.js (registro/creación):
    mínimo 8 caracteres, máximo 72 BYTES utf-8 (límite real de
    bcrypt), y debe incluir mayúscula, minúscula y número. No prohíbe
    espacios a propósito (ver comentario en validadores.js).
    """
    valor = valor or ""
    if not valor:
        raise ValueError("La contraseña es obligatoria.")
    if len(valor) < 8:
        raise ValueError("Debe tener al menos 8 caracteres.")
    if len(valor.encode("utf-8")) > MAX_BYTES_PASSWORD:
        raise ValueError(f"La contraseña es demasiado larga (máximo {MAX_BYTES_PASSWORD} bytes en UTF-8).")
    if not (re.search(r"[a-z]", valor) and re.search(r"[A-Z]", valor) and re.search(r"[0-9]", valor)):
        raise ValueError("Debe incluir una mayúscula, una minúscula y un número.")
    return valor


class UsuarioCrear(BaseModel):
    """
    Body de POST /api/usuarios/registro (registro público, siempre
    como `cliente`) y de POST /api/usuarios (creación desde el panel
    admin, que sí puede indicar `rol`) — mismos campos y reglas que
    RegisterModal.jsx y CrearUsuarioModal.jsx en el frontend.

    `rol` es opcional y por defecto `cliente`: el registro público no
    lo envía (queda en el default), mientras que el panel admin sí lo
    manda explícitamente. `activo` y `verificado` NO son parte de este
    esquema — los decide el backend según la ruta (registro público
    queda sin verificar; creación desde admin queda ya activo y
    verificado), nunca algo que el cliente HTTP pueda fijar.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str
    apellido: str
    tipo_documento: TipoDocumento
    numero_documento: str
    direccion: str
    telefono: str
    correo: EmailStr
    password: str
    rol: RolUsuario = RolUsuario.cliente
    # Solo lo exige/valida POST /api/usuarios/registro (ver
    # registrar_usuario en app/routes/usuarios.py) — la creación desde
    # el panel admin no representa el consentimiento del titular, así
    # que ese flujo lo ignora. Ver docs/POLITICA-TRATAMIENTO-DATOS.md.
    acepta_tratamiento_datos: bool = False

    @field_validator("nombre", "apellido")
    @classmethod
    def _valida_nombre(cls, v: str) -> str:
        return validar_nombre_propio(v)

    @field_validator("numero_documento")
    @classmethod
    def _valida_documento(cls, v: str) -> str:
        return validar_documento(v)

    @field_validator("direccion")
    @classmethod
    def _valida_direccion(cls, v: str) -> str:
        return validar_direccion(v)

    @field_validator("telefono")
    @classmethod
    def _valida_telefono(cls, v: str) -> str:
        return validar_telefono(v)

    @field_validator("correo")
    @classmethod
    def _valida_correo(cls, v: str) -> str:
        return validar_correo_largo(v)

    @field_validator("password")
    @classmethod
    def _valida_password(cls, v: str) -> str:
        return validar_password_nueva(v)


class UsuarioActualizar(BaseModel):
    """
    Body de la actualización de perfil propio (equivalente a
    `actualizarPerfil` en MiPerfil.jsx / PUT /api/usuarios/perfil).

    Deliberadamente NO incluye correo, documento, password, rol ni
    activo: el correo/documento son la identidad de la cuenta (no se
    editan aquí), la contraseña tiene su propio flujo
    (`cambiarPassword`, con contraseña actual + nueva — fuera del
    alcance de este esquema), y rol/activo los cambia un admin por
    endpoints dedicados (`cambiarRolUsuario`/`cambiarEstadoUsuario` en
    GestionUsuarios.jsx), nunca el propio usuario.

    Todos los campos son opcionales para permitir una actualización
    parcial; los que se envíen se validan con las mismas reglas que en
    la creación.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str | None = None
    apellido: str | None = None
    direccion: str | None = None
    telefono: str | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _valida_nombre(cls, v: str | None) -> str | None:
        return validar_nombre_propio(v) if v is not None else v

    @field_validator("direccion")
    @classmethod
    def _valida_direccion(cls, v: str | None) -> str | None:
        return validar_direccion(v) if v is not None else v

    @field_validator("telefono")
    @classmethod
    def _valida_telefono(cls, v: str | None) -> str | None:
        return validar_telefono(v) if v is not None else v


class UsuarioSalida(BaseModel):
    """
    Forma de un usuario en las respuestas de la API. Nunca incluye
    password_hash ni los campos internos de los códigos OTP de
    reset/verificación (reset_otp_hash, verificacion_otp_hash, etc.) —
    esos son exclusivamente del backend.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str
    tipo_documento: TipoDocumento
    numero_documento: str
    direccion: str
    telefono: str
    correo: EmailStr
    rol: RolUsuario
    activo: bool
    verificado: bool
    creado_en: datetime | None = None


class CambiarPasswordEntrada(BaseModel):
    """
    Body de PUT /api/usuarios/perfil/password: el propio usuario
    cambia su contraseña aportando la actual (para confirmar que es él
    quien la cambia, no solo alguien con el JWT ya cargado en una
    pestaña abierta) junto con la nueva. `password_nueva` sigue la
    misma regla de complejidad que en el registro/restablecimiento.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    password_actual: str
    password_nueva: str

    @field_validator("password_actual")
    @classmethod
    def _valida_password_actual(cls, v: str) -> str:
        if not v:
            raise ValueError("Debes ingresar tu contraseña actual.")
        return v

    @field_validator("password_nueva")
    @classmethod
    def _valida_password_nueva(cls, v: str) -> str:
        return validar_password_nueva(v)


class RolCambioEntrada(BaseModel):
    """
    Body de PUT /api/usuarios/{id}/rol: cambia el rol de un usuario
    (cliente/empleado/admin) desde el panel de administración. Ruta
    dedicada porque PUT /api/usuarios/{id} excluye `rol` a propósito
    (ver docstring de UsuarioActualizar).
    """

    rol: RolUsuario


class UsuarioEstadoEntrada(BaseModel):
    """
    Body de PATCH /api/usuarios/{id}/estado (equivalente a PUT
    /:id/estado en Node, expuesto como PATCH aquí por ser una
    actualización parcial de un solo campo). `activo` es obligatorio
    y debe ser explícitamente booleano — igual que la validación
    `typeof activo !== "boolean"` de Node, Pydantic ya rechaza con 422
    cualquier valor que no sea un bool real.
    """

    activo: bool

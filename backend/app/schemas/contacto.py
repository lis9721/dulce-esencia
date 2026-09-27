"""
Esquemas Pydantic de entrada/salida para /api/contacto.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.usuario import validar_nombre_propio


class ContactoCrear(BaseModel):
    """
    Body de POST /api/contacto (formulario público de contacto). Ruta
    sin autenticación: cualquier visitante puede escribir, no solo
    usuarios registrados.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str
    correo: EmailStr
    mensaje: str

    @field_validator("nombre")
    @classmethod
    def _valida_nombre(cls, v: str) -> str:
        return validar_nombre_propio(v)

    @field_validator("correo")
    @classmethod
    def _valida_correo(cls, v: str) -> str:
        if len(v) > 60:
            raise ValueError("Debe tener máximo 60 caracteres.")
        return v

    @field_validator("mensaje")
    @classmethod
    def _valida_mensaje(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("El mensaje es obligatorio.")
        if len(v) < 10:
            raise ValueError("Debe tener al menos 10 caracteres.")
        if len(v) > 2000:
            raise ValueError("Debe tener máximo 2000 caracteres.")
        return v


class ContactoSalida(BaseModel):
    """Forma de un mensaje de contacto en las respuestas de la API (solo para admin/empleado)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    correo: EmailStr
    mensaje: str
    creado_en: datetime | None = None

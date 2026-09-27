from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class ResenaCrear(BaseModel):
    """Body de POST /api/productos/{producto_id}/resenas."""

    model_config = ConfigDict(str_strip_whitespace=True)

    calificacion: int
    comentario: str | None = None

    @field_validator("calificacion")
    @classmethod
    def _valida_calificacion(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("La calificación debe estar entre 1 y 5.")
        return v

    @field_validator("comentario")
    @classmethod
    def _valida_comentario(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 500:
            raise ValueError("El comentario debe tener máximo 500 caracteres.")
        return v


class ResenaUsuarioResumen(BaseModel):
    """Solo el nombre del autor — nunca su correo ni otros datos personales en una respuesta pública."""

    model_config = ConfigDict(from_attributes=True)

    nombre: str


class ResenaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    usuario_id: int
    calificacion: int
    comentario: str | None = None
    creado_en: datetime | None = None
    usuario: ResenaUsuarioResumen | None = None

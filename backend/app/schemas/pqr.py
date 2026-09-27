"""Esquemas Pydantic de entrada/salida para /api/pqr."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.pqr import EstadoPQR, TipoPQR


class PQRCrear(BaseModel):
    """Body de POST /api/pqr — el cliente registra su solicitud."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"tipo": "reclamo", "asunto": "Mi pedido llegó incompleto", "descripcion": "Pedí dos cajas de cupcakes y solo recibí una; adjunto el número de pedido."}]})

    tipo: TipoPQR = TipoPQR.peticion
    asunto: str
    descripcion: str

    @field_validator("asunto")
    @classmethod
    def _valida_asunto(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("El asunto es obligatorio.")
        if len(v) > 120:
            raise ValueError("El asunto debe tener máximo 120 caracteres.")
        return v

    @field_validator("descripcion")
    @classmethod
    def _valida_descripcion(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 10:
            raise ValueError("Cuéntanos un poco más — mínimo 10 caracteres.")
        if len(v) > 2000:
            raise ValueError("La descripción debe tener máximo 2000 caracteres.")
        return v


class PQRActualizar(BaseModel):
    """Body de PATCH /api/pqr/{id} — solo admin/empleado (gestión y respuesta)."""

    estado: EstadoPQR | None = None
    respuesta: str | None = None

    @field_validator("respuesta")
    @classmethod
    def _valida_respuesta(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("La respuesta debe tener máximo 2000 caracteres.")
        return v or None


class PQRSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    tipo: TipoPQR
    asunto: str
    descripcion: str
    estado: EstadoPQR
    respuesta: str | None = None
    respondido_por_id: int | None = None
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None

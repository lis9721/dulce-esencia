"""Esquemas Pydantic de entrada/salida para /api/facturas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.factura import EstadoFactura


class FacturaCrear(BaseModel):
    """Body de POST /api/facturas: genera la factura de una venta ya registrada."""

    venta_id: int


class DetalleFacturaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    precio_unitario: float
    cantidad: int
    subtotal: float


class FacturaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    venta_id: int
    cliente_id: int
    subtotal: float
    impuestos: float
    total: float
    estado: EstadoFactura
    creado_en: datetime | None = None
    items: list[DetalleFacturaSalida] = []


class FacturaFiltros(BaseModel):
    numero: str | None = None
    cliente_id: int | None = None
    fecha: date | None = None

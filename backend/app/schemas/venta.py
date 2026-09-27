"""Esquemas Pydantic de entrada/salida para /api/ventas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.venta import EstadoVenta


class VentaItemEntrada(BaseModel):
    """
    Un ítem de venta al registrarla: exactamente uno de producto_id/
    servicio_id debe venir informado (nunca los dos, nunca ninguno) —
    misma regla que el CheckConstraint del modelo DetalleVenta.
    """

    producto_id: int | None = None
    servicio_id: int | None = None
    cantidad: int

    @field_validator("cantidad")
    @classmethod
    def _valida_cantidad(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("La cantidad debe ser mayor a 0.")
        return v

    @model_validator(mode="after")
    def _valida_producto_xor_servicio(self):
        if bool(self.producto_id) == bool(self.servicio_id):
            raise ValueError("Cada ítem debe indicar producto_id O servicio_id, no ambos ni ninguno.")
        return self


class VentaCrear(BaseModel):
    """
    Body de POST /api/ventas: registra una venta directa (punto de
    venta) de productos y/o servicios para un cliente ya existente.
    El precio de cada ítem SIEMPRE se toma del catálogo en el servidor
    (igual que en el checkout de pedidos) — nunca del precio que mande
    el cliente HTTP.
    """

    cliente_id: int
    items: list[VentaItemEntrada]
    descuento: float = 0
    impuestos: float = 0
    notas: str | None = None

    @field_validator("items")
    @classmethod
    def _valida_items(cls, v: list[VentaItemEntrada]) -> list[VentaItemEntrada]:
        if not v:
            raise ValueError("La venta debe tener al menos un ítem.")
        return v

    @field_validator("descuento", "impuestos")
    @classmethod
    def _valida_no_negativo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("No puede ser negativo.")
        return v

    @field_validator("notas")
    @classmethod
    def _valida_notas(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 255:
            raise ValueError("Las notas deben tener máximo 255 caracteres.")
        return v or None


class VentaEstadoEntrada(BaseModel):
    estado: EstadoVenta


class DetalleVentaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int | None = None
    servicio_id: int | None = None
    nombre: str
    precio_unitario: float
    cantidad: int
    subtotal: float


class VentaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    vendedor_id: int | None = None
    pedido_id: int | None = None
    subtotal: float
    descuento: float
    impuestos: float
    total: float
    estado: EstadoVenta
    notas: str | None = None
    creado_en: datetime | None = None
    items: list[DetalleVentaSalida] = []


class VentaFiltros(BaseModel):
    """Criterios de consulta del historial de ventas — GET /api/ventas."""

    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    cliente_id: int | None = None
    producto_id: int | None = None
    servicio_id: int | None = None
    estado: EstadoVenta | None = None

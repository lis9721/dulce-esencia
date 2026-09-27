"""
Modelo de factura de venta (Quinto Avance).

Una Factura se genera SIEMPRE a partir de una Venta ya registrada
(POST /api/facturas con venta_id) — nunca se crea "suelta". Sus ítems
(DetalleFactura) son una copia congelada de los ítems de la venta en
el momento de facturar, igual que el criterio ya usado en
pedido_items/detalle_ventas: si después alguien anula la venta o el
producto cambia de precio, la factura ya emitida no se altera.
"""

import enum

from sqlalchemy import TIMESTAMP, CheckConstraint, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoFactura(str, enum.Enum):
    emitida = "emitida"
    anulada = "anulada"


class Factura(Base):
    __tablename__ = "facturas"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_facturas_numero"),
        CheckConstraint("subtotal >= 0", name="chk_facturas_subtotal"),
        CheckConstraint("impuestos >= 0", name="chk_facturas_impuestos"),
        CheckConstraint("total >= 0", name="chk_facturas_total"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    venta_id: Mapped[int] = mapped_column(Integer, ForeignKey("ventas.id"), nullable=False, unique=True)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    impuestos: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[EstadoFactura] = mapped_column(Enum(EstadoFactura), nullable=False, default=EstadoFactura.emitida)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    venta = relationship("Venta", back_populates="factura")
    # `cliente_id`/`cliente` ya NO son columnas propias: antes duplicaban
    # (dependencia transitiva factura → venta → cliente, ver
    # docs/NORMALIZACION-BD.md) un dato que ya vive en `ventas.cliente_id`.
    # El association_proxy lee/filtra a través de `venta` sin guardar nada
    # dos veces, y sigue funcionando en Python (`factura.cliente_id`) y en
    # consultas (`Factura.cliente_id == valor`).
    cliente_id = association_proxy("venta", "cliente_id")
    cliente = association_proxy("venta", "cliente")
    items = relationship("DetalleFactura", back_populates="factura", cascade="all, delete-orphan")


class DetalleFactura(Base):
    __tablename__ = "detalle_facturas"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_detalle_facturas_cantidad"),
        CheckConstraint("precio_unitario >= 0", name="chk_detalle_facturas_precio"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factura_id: Mapped[int] = mapped_column(Integer, ForeignKey("facturas.id", ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    factura = relationship("Factura", back_populates="items")

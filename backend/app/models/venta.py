"""
Modelos de venta (Quinto Avance — módulo de gestión comercial).

Una Venta es el registro comercial "de punto de venta": la puede crear
directamente un admin/empleado (venta presencial o telefónica, de
productos y/o servicios) o puede generarse automáticamente a partir de
un Pedido del sitio web que ya fue marcado como `pagado` (ver
POST /api/ventas/desde-pedido/{pedido_id} en app/routes/ventas.py), sin
duplicar la lógica de checkout/carrito que ya vive en app/models/pedido.py.

Se modela aparte de Pedido (en vez de reutilizarlo) porque el quinto
avance pide explícitamente que la venta pueda incluir SERVICIOS además
de productos (pedidos/pedido_items solo maneja productos), y porque el
enunciado pide tablas propias `ventas`/`detalle_ventas`.
"""

import enum

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoVenta(str, enum.Enum):
    completada = "completada"
    anulada = "anulada"


class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="chk_ventas_subtotal"),
        CheckConstraint("descuento >= 0", name="chk_ventas_descuento"),
        CheckConstraint("impuestos >= 0", name="chk_ventas_impuestos"),
        CheckConstraint("total >= 0", name="chk_ventas_total"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False)
    # Usuario (admin/empleado) que registró la venta. Nula cuando la
    # venta se generó automáticamente desde un pedido del sitio web
    # (ver pedido_id) y nadie del staff la tecleó a mano.
    vendedor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=True)
    # Si la venta nació de un pedido del sitio web (checkout normal),
    # queda enlazada aquí — 1 pedido genera como máximo 1 venta.
    pedido_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pedidos.id"), nullable=True, unique=True
    )
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    descuento: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    impuestos: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    estado: Mapped[EstadoVenta] = mapped_column(Enum(EstadoVenta), nullable=False, default=EstadoVenta.completada)
    notas: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    cliente = relationship("Usuario", foreign_keys=[cliente_id])
    vendedor = relationship("Usuario", foreign_keys=[vendedor_id])
    pedido = relationship("Pedido")
    items = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    factura = relationship("Factura", back_populates="venta", uselist=False, cascade="all, delete-orphan")


class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_detalle_ventas_cantidad"),
        CheckConstraint("precio_unitario >= 0", name="chk_detalle_ventas_precio"),
        CheckConstraint(
            "(producto_id IS NOT NULL AND servicio_id IS NULL) OR "
            "(producto_id IS NULL AND servicio_id IS NOT NULL)",
            name="chk_detalle_ventas_producto_xor_servicio",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(Integer, ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False)
    producto_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("productos.id"), nullable=True)
    servicio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("servicios.id"), nullable=True)
    # Nombre y precio se congelan al momento de la venta, igual que en
    # pedido_items — la venta histórica no cambia si el producto o
    # servicio cambia de precio/nombre después.
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    venta = relationship("Venta", back_populates="items")
    producto = relationship("Producto")
    servicio = relationship("Servicio")

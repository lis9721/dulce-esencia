import datetime as dt
import enum

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoPedido(str, enum.Enum):
    pendiente = "pendiente"
    pagado = "pagado"
    enviado = "enviado"
    entregado = "entregado"
    cancelado = "cancelado"


class MetodoPago(str, enum.Enum):
    tarjeta = "tarjeta"
    transferencia = "transferencia"
    contraentrega = "contraentrega"


class TipoEntrega(str, enum.Enum):
    domicilio = "domicilio"
    recoger_tienda = "recoger_tienda"


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint("usuario_id", "idempotency_key", name="uq_pedido_idempotencia"),
        CheckConstraint("subtotal >= 0", name="chk_pedidos_subtotal"),
        CheckConstraint("descuento >= 0", name="chk_pedidos_descuento"),
        CheckConstraint("total >= 0", name="chk_pedidos_total"),
        CheckConstraint("subtotal >= descuento", name="chk_pedidos_subtotal_descuento"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estado: Mapped[EstadoPedido] = mapped_column(Enum(EstadoPedido), nullable=False, default=EstadoPedido.pendiente)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    descuento: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    cupon_codigo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Se deja NOT NULL a propósito (no se toca la nulabilidad de una
    # columna que ya existe físicamente en producción — sincronizar_esquema()
    # solo agrega columnas nuevas, no relaja NOT NULL de una existente).
    # Cuando tipo_entrega=recoger_tienda, el router guarda un texto fijo
    # ("Recoge en tienda — <sede>") en vez de dejarla vacía; ver
    # app/routes/pedidos.py.
    direccion_envio: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono_contacto: Mapped[str] = mapped_column(String(15), nullable=False)
    metodo_pago: Mapped[MetodoPago] = mapped_column(Enum(MetodoPago), nullable=False)
    # Recoger en tienda vs. domicilio, y la ventana horaria pedida por
    # el cliente — importante en una pastelería: nadie quiere una torta
    # entregada 3 horas después de la hora del evento. `default` con un
    # valor fijo hace que sincronizar_esquema() pueda rellenar con él
    # las filas ya existentes (pedidos creados antes de este cambio, que
    # todos eran a domicilio).
    tipo_entrega: Mapped[TipoEntrega] = mapped_column(
        Enum(TipoEntrega), nullable=False, default=TipoEntrega.domicilio
    )
    fecha_entrega_solicitada: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    franja_horaria: Mapped[str | None] = mapped_column(String(50), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship("PedidoItem", back_populates="pedido", cascade="all, delete-orphan")


class PedidoItem(Base):
    __tablename__ = "pedido_items"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_pedido_items_cantidad"),
        CheckConstraint("precio_unitario >= 0", name="chk_pedido_items_precio"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_id: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id"), nullable=False)
    # titulo/precio_unitario se congelan al momento de la compra (no se
    # recalculan contra productos): así, si el producto cambia de precio
    # o se despublica después, la factura histórica no se altera.
    titulo: Mapped[str] = mapped_column(String(80), nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)

    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto")

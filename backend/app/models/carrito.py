from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Carrito(Base):
    __tablename__ = "carritos"
    __table_args__ = (UniqueConstraint("usuario_id", name="uq_carrito_usuario"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    usuario = relationship("Usuario", back_populates="carrito")
    items = relationship("CarritoItem", back_populates="carrito", cascade="all, delete-orphan")


class CarritoItem(Base):
    __tablename__ = "carrito_items"
    __table_args__ = (
        UniqueConstraint("carrito_id", "producto_id", name="uq_carrito_producto"),
        CheckConstraint("cantidad > 0", name="chk_carrito_items_cantidad"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    carrito_id: Mapped[int] = mapped_column(Integer, ForeignKey("carritos.id", ondelete="CASCADE"), nullable=False)
    producto_id: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    agregado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    carrito = relationship("Carrito", back_populates="items")
    producto = relationship("Producto")

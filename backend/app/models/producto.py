import enum

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FamiliaProducto(str, enum.Enum):
    """Categoría comercial de un producto de la pastelería (vitrina)."""

    tortas = "tortas"
    cupcakes = "cupcakes"
    galletas = "galletas"
    postres = "postres"
    hojaldres = "hojaldres"
    panaderia = "panaderia"


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_productos_sku"),
        CheckConstraint("precio >= 0", name="chk_productos_precio"),
        CheckConstraint("stock >= 0", name="chk_productos_stock"),
        # El catálogo se filtra por proveedor en el panel: índice explícito
        # sobre la clave foránea (criterio 48).
        Index("ix_productos_proveedor", "proveedor_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(80), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    imagen: Mapped[str] = mapped_column(String(120), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sku: Mapped[str | None] = mapped_column(String(30), nullable=True)
    familia: Mapped[FamiliaProducto] = mapped_column(
        Enum(FamiliaProducto), nullable=False, default=FamiliaProducto.tortas
    )
    peso_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Denormalizado a propósito (en vez de calcular AVG/COUNT contra
    # `resenas` en cada consulta del catálogo): se recalculan estas dos
    # columnas cada vez que se crea/edita/borra una reseña (ver
    # app/routes/resenas.py) para que listar el catálogo con estrellas
    # no dispare una subconsulta de agregación por producto.
    calificacion_promedio: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False, default=0)
    total_resenas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    # Proveedor que surte este producto (módulo de proveedores).
    # Es NULL-able a propósito: el catálogo ya existía antes que la tabla
    # `proveedores`, y obligar el campo dejaría sin migrar los productos
    # ya cargados. ondelete="RESTRICT" es la barrera a nivel de base de
    # datos que respalda el 409 de ProveedorConProductos: borrar un
    # proveedor que todavía surte productos no puede dejar filas huérfanas.
    proveedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("proveedores.id", ondelete="RESTRICT", name="fk_productos_proveedor"),
        nullable=True,
    )
    # Destino por cadena, igual que en app/models/proveedor.py: evita el
    # import circular entre ambos módulos. lazy="joined" trae el
    # proveedor en la MISMA consulta del producto, para que
    # ProductoSalida.proveedor (esquema Resumen) nunca dispare una carga
    # perezosa al serializar (criterio 55).
    proveedor = relationship(
        "Proveedor",
        back_populates="productos",
        lazy="joined",
    )
    resenas = relationship("Resena", back_populates="producto", cascade="all, delete-orphan")

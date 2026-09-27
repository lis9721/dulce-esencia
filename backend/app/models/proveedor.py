"""
Modelo ORM de `proveedores` (criterios 46, 47 y 48 de la lista de
chequeo).

Estilo SQLAlchemy 2.x: `DeclarativeBase` (app/database.py) + `Mapped[...]`
+ `mapped_column(...)`, nunca la sintaxis antigua `Column(...)` sin
anotar.

Relaciones (criterio 47)
------------------------
    proveedores 1 ──< productos ──< pedido_items ──> pedidos ──> usuarios

`Producto.proveedor_id` es la clave foránea que incorpora esta entidad
al modelo de datos ya existente, así que el catálogo deja de tener el
origen de cada producto como texto suelto y pasa a apuntar a un
registro real.

Índices y unicidad (criterio 48)
--------------------------------
  * `nit` es único: identifica al proveedor ante la DIAN, no puede
    repetirse.
  * `razon_social` es única: evita dar de alta dos veces al mismo
    proveedor con NIT mal digitado.
  * Índices en `estado` y `categoria` porque son justamente los dos
    filtros del listado del panel (WHERE estado = ... AND categoria = ...).
"""

import enum
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Enum,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CategoriaProveedor(str, enum.Enum):
    """Qué le compra Dulce Esencia a este proveedor."""

    materias_primas = "materias_primas"  # harinas, azúcar, cacao, chocolate
    lacteos = "lacteos"                  # leche, crema, mantequilla, queso y huevos
    empaques = "empaques"                # cajas, bases, moldes, bolsas
    insumos = "insumos"                  # colorantes, esencias, decoración comestible
    logistica = "logistica"              # transporte refrigerado y mensajería


class EstadoProveedor(str, enum.Enum):
    """
    Estado comercial. Lo decide SIEMPRE el servidor (nunca llega en el
    cuerpo de un POST/PUT — criterio 5): se cambia con los sub-recursos
    POST /proveedores/{id}/suspensiones y /reactivaciones.
    """

    activo = "activo"
    suspendido = "suspendido"


class Proveedor(Base):
    __tablename__ = "proveedores"
    __table_args__ = (
        UniqueConstraint("nit", name="uq_proveedores_nit"),
        UniqueConstraint("razon_social", name="uq_proveedores_razon_social"),
        CheckConstraint("dias_credito >= 0 AND dias_credito <= 180", name="chk_proveedores_dias_credito"),
        CheckConstraint("cupo_credito >= 0", name="chk_proveedores_cupo_credito"),
        CheckConstraint(
            "calificacion IS NULL OR (calificacion >= 1 AND calificacion <= 5)",
            name="chk_proveedores_calificacion",
        ),
        Index("ix_proveedores_estado", "estado"),
        Index("ix_proveedores_categoria", "categoria"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Identificación ---
    razon_social: Mapped[str] = mapped_column(String(120), nullable=False)
    nit: Mapped[str] = mapped_column(String(20), nullable=False)
    categoria: Mapped[CategoriaProveedor] = mapped_column(
        Enum(CategoriaProveedor), nullable=False, default=CategoriaProveedor.materias_primas
    )

    # --- Contacto ---
    contacto_nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    correo: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(60), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sitio_web: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # --- Condiciones comerciales ---
    dias_credito: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cupo_credito: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    calificacion: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)

    # --- Estado (server-side) ---
    estado: Mapped[EstadoProveedor] = mapped_column(
        Enum(EstadoProveedor), nullable=False, default=EstadoProveedor.activo
    )
    motivo_suspension: Mapped[str | None] = mapped_column(String(200), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    actualizado_en: Mapped[datetime | None] = mapped_column(
        TIMESTAMP, nullable=True, onupdate=func.current_timestamp()
    )

    # Lado "uno" de la relación con productos. lazy="selectin" evita el
    # N+1 y, sobre todo, evita que un atributo quede sin cargar cuando el
    # esquema de salida lo serializa fuera del `with` de la sesión
    # (criterio 55).
    # El destino se declara como cadena ("Producto") y se resuelve por el
    # registro de SQLAlchemy: así `proveedores` y `productos` pueden
    # referenciarse mutuamente sin que sus módulos se importen en
    # círculo. Las COLUMNAS sí usan Mapped/mapped_column (criterio 46);
    # la anotación es opcional en relationship() y aquí se omite a
    # propósito por ese motivo.
    productos = relationship(
        "Producto",
        back_populates="proveedor",
        lazy="selectin",
    )

    @property
    def total_productos(self) -> int:
        """
        Cuántos productos del catálogo surte este proveedor. Lo consume
        `ProveedorSalida.total_productos` (`from_attributes=True`).

        Se apoya en la relación con `lazy="selectin"`: la colección ya
        viene cargada en la MISMA consulta del listado, así que contar
        aquí no dispara una consulta extra por fila (nada de N+1) ni deja
        un atributo perezoso pendiente cuando Pydantic serializa fuera
        de la sesión (criterio 55).
        """
        return len(self.productos)

    def __repr__(self) -> str:  # pragma: no cover - ayuda al depurar
        return f"<Proveedor id={self.id} nit={self.nit!r} estado={self.estado}>"

"""
Reseñas/calificaciones de productos — "compra verificada": solo puede
reseñar un producto quien tiene al menos un pedido PAGADO (o entregado)
que lo incluya (ver _validar_compra_verificada en app/routes/resenas.py).
Evita el spam de reseñas de quien nunca compró nada, sin ser tan
estricto como exigir "entregado" (que depende de que el admin/empleado
marque el pedido a mano).
"""

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resena(Base):
    __tablename__ = "resenas"
    __table_args__ = (
        # Una reseña por producto y por usuario — para cambiar de
        # opinión se edita/borra la propia (ver PUT/DELETE en
        # app/routes/resenas.py), no se acumulan varias.
        UniqueConstraint("producto_id", "usuario_id", name="uq_resenas_producto_usuario"),
        CheckConstraint("calificacion >= 1 AND calificacion <= 5", name="chk_resenas_calificacion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    calificacion: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    producto = relationship("Producto", back_populates="resenas")
    usuario = relationship("Usuario")

from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Servicio(Base):
    __tablename__ = "servicios"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_servicios_codigo"),
        CheckConstraint("precio >= 0", name="chk_servicios_precio"),
        CheckConstraint("duracion_minutos IS NULL OR duracion_minutos > 0", name="chk_servicios_duracion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    duracion_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imagen: Mapped[str | None] = mapped_column(String(120), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    codigo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

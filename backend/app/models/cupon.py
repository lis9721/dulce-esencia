import enum

from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, DateTime, Enum, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TipoCupon(str, enum.Enum):
    porcentaje = "porcentaje"
    monto_fijo = "monto_fijo"


class Cupon(Base):
    __tablename__ = "cupones"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_cupon_codigo"),
        CheckConstraint("valor >= 0", name="chk_cupones_valor"),
        CheckConstraint("monto_minimo >= 0", name="chk_cupones_monto_minimo"),
        CheckConstraint("usos_actuales >= 0", name="chk_cupones_usos_actuales"),
        CheckConstraint("valido_hasta >= valido_desde", name="chk_cupones_vigencia"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo: Mapped[TipoCupon] = mapped_column(Enum(TipoCupon), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    monto_minimo: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    usos_maximos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usos_actuales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valido_desde = mapped_column(DateTime, nullable=False)
    valido_hasta = mapped_column(DateTime, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

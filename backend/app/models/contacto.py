from sqlalchemy import TIMESTAMP, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MensajeContacto(Base):
    __tablename__ = "mensajes_contacto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    correo: Mapped[str] = mapped_column(String(60), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

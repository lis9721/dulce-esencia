"""
Modelos del Chatbot con IA (Quinto Avance): conversaciones y mensajes.

Una Conversacion agrupa los Mensajes de un intercambio con el chatbot.
`usuario_id` es NULO cuando el visitante todavía no inició sesión (el
chatbot igual debe poder orientar a un invitado sobre productos,
servicios y el proceso de compra); si el visitante SÍ tiene sesión, se
guarda para poder mostrarle su propio historial y para poder crear una
PQR asociada a su cuenta cuando el chatbot la origina.
"""

import enum

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RolMensaje(str, enum.Enum):
    usuario = "usuario"
    asistente = "asistente"


class Conversacion(Base):
    __tablename__ = "conversaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=True)
    # Identificador de sesión de navegador para invitados sin cuenta,
    # así el frontend puede seguir mostrando el mismo hilo de chat
    # aunque el visitante no esté autenticado.
    sesion_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    usuario = relationship("Usuario")
    mensajes = relationship(
        "Mensaje", back_populates="conversacion", cascade="all, delete-orphan", order_by="Mensaje.id"
    )


class Mensaje(Base):
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversacion_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversaciones.id", ondelete="CASCADE"), nullable=False
    )
    rol: Mapped[RolMensaje] = mapped_column(Enum(RolMensaje), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    conversacion = relationship("Conversacion", back_populates="mensajes")

"""
Modelo de PQR (Peticiones, Quejas y Reclamos) — Quinto Avance.

El cliente registra una PQR y puede consultar su estado; admin/empleado
la gestionan (cambian estado y/o responden). También se usa como
destino cuando el Chatbot detecta que una conversación debe escalarse
a un humano (ver app/models/chatbot.py / app/routes/chatbot.py).
"""

import enum

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoPQR(str, enum.Enum):
    peticion = "peticion"
    queja = "queja"
    reclamo = "reclamo"
    sugerencia = "sugerencia"


class EstadoPQR(str, enum.Enum):
    pendiente = "pendiente"
    en_proceso = "en_proceso"
    respondida = "respondida"
    cerrada = "cerrada"


class PQR(Base):
    __tablename__ = "pqr"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo: Mapped[TipoPQR] = mapped_column(Enum(TipoPQR), nullable=False, default=TipoPQR.peticion)
    asunto: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoPQR] = mapped_column(Enum(EstadoPQR), nullable=False, default=EstadoPQR.pendiente)
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    respondido_por_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=True)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    actualizado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    cliente = relationship("Usuario", foreign_keys=[cliente_id])
    respondido_por = relationship("Usuario", foreign_keys=[respondido_por_id])

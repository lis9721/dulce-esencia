import enum
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoDocumento(str, enum.Enum):
    CC = "CC"
    TI = "TI"
    CE = "CE"
    PA = "PA"


class RolUsuario(str, enum.Enum):
    cliente = "cliente"
    empleado = "empleado"
    admin = "admin"


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("correo", name="uq_usuarios_correo"),
        UniqueConstraint("tipo_documento", "numero_documento", name="uq_usuarios_documento"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(40), nullable=False)
    apellido: Mapped[str] = mapped_column(String(40), nullable=False)
    tipo_documento: Mapped[TipoDocumento] = mapped_column(Enum(TipoDocumento), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(15), nullable=False)
    direccion: Mapped[str] = mapped_column(String(100), nullable=False)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    correo: Mapped[str] = mapped_column(String(60), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # FK a roles.nombre (no ENUM): antes `rol` era un ENUM que describía el
    # mismo dominio que la tabla `roles` sin ninguna llave foránea entre
    # ambos (dependencia transitiva/redundancia — ver
    # docs/NORMALIZACION-BD.md). RolUsuario se conserva solo como el
    # validador de los 3 valores permitidos en los esquemas Pydantic; la
    # fuente de verdad del dominio pasa a ser la tabla `roles`.
    rol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("roles.nombre", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
        default="cliente",
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Prueba de que el usuario aceptó la política de tratamiento de
    # datos personales al registrarse (Ley 1581 de 2012 / Habeas Data,
    # Colombia — ver docs/POLITICA-TRATAMIENTO-DATOS.md). Se guarda la
    # FECHA de aceptación, no un simple booleano: si la política cambia
    # más adelante, esta columna permite saber quién aceptó bajo cuál
    # versión. NULL en cuentas creadas antes de este cambio o por el
    # panel admin (que no pasa por el consentimiento del titular).
    tratamiento_datos_aceptado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- OTP de restablecimiento de contraseña ("olvidé mi contraseña") ---
    # reset_otp_hash guarda el SHA-256 del código de 6 dígitos, NUNCA el
    # código en texto plano (igual criterio que password_hash). intentos
    # cuenta los intentos fallidos consecutivos contra ESTE código: al
    # llegar a MAX_INTENTOS_OTP (ver routes/usuarios.py) el código se
    # invalida aunque no haya expirado, para frenar fuerza bruta sobre un
    # espacio de solo 10^6 combinaciones.
    reset_otp_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_otp_expira: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    reset_otp_intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- OTP de verificación de correo (segundo paso del registro) ---
    # Mismo patrón y mismo motivo que reset_otp_* arriba.
    verificacion_otp_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verificacion_otp_expira: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    verificacion_otp_intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

    carrito = relationship("Carrito", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="usuario")

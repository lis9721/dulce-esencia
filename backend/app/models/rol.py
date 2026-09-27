from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Rol(Base):
    """
    `usuarios.rol` es una llave foránea a `roles.nombre` (ver
    app/models/usuario.py y docs/NORMALIZACION-BD.md), así que esta tabla
    ya es la fuente de verdad del DOMINIO de roles válidos. El control de
    acceso en sí (qué puede hacer cada rol) lo sigue decidiendo el código
    por ruta vía requiere_rol() (app/auth.py); `permisos`/`rol_permisos`
    siguen siendo solo datos consultables para el panel de administración,
    sincronizados a mano con esas reglas.
    """

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("nombre", name="uq_roles_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(150), nullable=False)

    permisos = relationship("Permiso", secondary="rol_permisos", back_populates="roles")


class Permiso(Base):
    __tablename__ = "permisos"
    __table_args__ = (UniqueConstraint("clave", name="uq_permisos_clave"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(150), nullable=False)

    roles = relationship("Rol", secondary="rol_permisos", back_populates="permisos")


class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    rol_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permiso_id: Mapped[int] = mapped_column(Integer, ForeignKey("permisos.id", ondelete="CASCADE"), primary_key=True)

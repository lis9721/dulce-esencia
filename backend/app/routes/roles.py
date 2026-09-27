"""
Router de /api/roles.

Solo lectura, como explica el docstring de app/models/rol.py:
`usuarios.rol` es FK a `roles.nombre`, pero qué puede hacer cada rol lo
sigue decidiendo requiere_rol() (app/auth.py). Esto solo expone esa
información como datos consultables para el panel de administración.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import requiere_rol
from app.database import get_db
from app.models.rol import Rol
from app.schemas.rol import RolSalida

router = APIRouter(
    prefix="/api/roles",
    tags=["roles"],
    dependencies=[Depends(requiere_rol("admin"))],
)


@router.get("", response_model=list[RolSalida])
def listar_roles(db: Session = Depends(get_db)):
    """Lista todos los roles junto con sus permisos. Ruta PROTEGIDA solo para admin."""
    roles = db.query(Rol).options(joinedload(Rol.permisos)).order_by(Rol.id.asc()).all()
    return roles


@router.get("/{rol_id}", response_model=RolSalida)
def obtener_rol(rol_id: int, db: Session = Depends(get_db)):
    """Detalle de un rol con sus permisos. Ruta PROTEGIDA solo para admin."""
    rol = (
        db.query(Rol)
        .options(joinedload(Rol.permisos))
        .filter(Rol.id == rol_id)
        .first()
    )
    if rol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
    return rol

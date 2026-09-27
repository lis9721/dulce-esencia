"""
Esquemas Pydantic de salida para /api/roles.

Sin esquemas de entrada: `usuarios.rol` es FK a `roles.nombre` (ver
app/models/usuario.py), pero qué puede hacer cada rol lo sigue
decidiendo requiere_rol() por ruta (app/auth.py). /api/roles solo
expone roles/permisos como datos consultables para el panel de
administración, no permite crearlos ni editarlos desde la API.
"""

from pydantic import BaseModel, ConfigDict


class PermisoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clave: str
    descripcion: str


class RolSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str
    permisos: list[PermisoSalida] = []

"""
Router de /api/servicios.

Misma estructura que routes/productos.py: catálogo público (GET) +
gestión protegida (POST/PUT/PATCH/DELETE) para GestionServicios.jsx.
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import requiere_rol
from app.database import get_db
from app.models.servicio import Servicio
from app.schemas.servicio import ServicioActualizar, ServicioCrear, ServicioSalida
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion
from app.utils.busqueda import CARACTER_ESCAPE, patron_contiene

router = APIRouter(prefix="/api/servicios", tags=["servicios"])
DIRECTORIO_IMAGENES_SERVICIOS = "uploads/servicios"
EXTENSIONES_IMAGEN_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES_IMAGEN = 5 * 1024 * 1024


@router.post(
    "/imagen",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
async def subir_imagen_servicio(imagen: UploadFile = File(...)):
    """Sube una imagen de servicio a uploads/servicios y devuelve la ruta pública."""
    extension = os.path.splitext(imagen.filename or "")[1].lower()
    if extension not in EXTENSIONES_IMAGEN_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen debe ser .jpg, .jpeg, .png o .webp.",
        )

    contenido = await imagen.read()
    if len(contenido) > MAX_BYTES_IMAGEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no puede pesar más de 5 MB.",
        )

    os.makedirs(DIRECTORIO_IMAGENES_SERVICIOS, exist_ok=True)
    nombre_archivo = f"{uuid.uuid4().hex}{extension}"
    with open(os.path.join(DIRECTORIO_IMAGENES_SERVICIOS, nombre_archivo), "wb") as destino:
        destino.write(contenido)

    return {"ruta_imagen": f"/uploads/servicios/{nombre_archivo}"}


@router.get("", response_model=None)
def listar_servicios(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    buscar: str | None = Query(default=None, max_length=60),
    db: Session = Depends(get_db),
):
    """
    Catálogo público de servicios, paginado. Ruta PÚBLICA — solo
    muestra servicios `activo=True`; para ver también los inactivos
    usa GET /api/servicios/admin/todos (rol admin/empleado).
    """
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    consulta = db.query(Servicio).filter(Servicio.activo.is_(True))
    if buscar:
        consulta = consulta.filter(Servicio.nombre.ilike(patron_contiene(buscar), escape=CARACTER_ESCAPE))

    total = consulta.count()
    servicios = consulta.order_by(Servicio.orden.asc(), Servicio.id.desc()).offset(offset).limit(limite_final).all()

    return {
        "datos": [ServicioSalida.model_validate(s) for s in servicios],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get(
    "/admin/todos",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def listar_servicios_admin(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Listado completo (activos e inactivos) para GestionServicios.jsx. Ruta PROTEGIDA para admin y empleado."""
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    total = db.query(Servicio).count()
    servicios = (
        db.query(Servicio)
        .order_by(Servicio.orden.asc(), Servicio.id.desc())
        .offset(offset)
        .limit(limite_final)
        .all()
    )

    return {
        "datos": [ServicioSalida.model_validate(s) for s in servicios],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get("/{servicio_id}", response_model=ServicioSalida)
def obtener_servicio(servicio_id: int, db: Session = Depends(get_db)):
    """Detalle de un servicio por id. Ruta PÚBLICA."""
    servicio = db.get(Servicio, servicio_id)
    if servicio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado.")
    return servicio


@router.post(
    "",
    response_model=ServicioSalida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def crear_servicio(datos: ServicioCrear, db: Session = Depends(get_db)):
    """Crea un servicio nuevo. Ruta PROTEGIDA para admin y empleado."""
    servicio = Servicio(**datos.model_dump())
    db.add(servicio)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un servicio con ese código.",
        ) from None
    db.refresh(servicio)
    return servicio


@router.put(
    "/{servicio_id}",
    response_model=ServicioSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def actualizar_servicio(servicio_id: int, datos: ServicioActualizar, db: Session = Depends(get_db)):
    """Reemplaza todos los campos editables de un servicio. Ruta PROTEGIDA para admin y empleado."""
    servicio = db.get(Servicio, servicio_id)
    if servicio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado.")

    for campo, valor in datos.model_dump().items():
        setattr(servicio, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un servicio con ese código.",
        ) from None
    db.refresh(servicio)
    return servicio


@router.patch(
    "/{servicio_id}/estado",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def cambiar_estado_servicio(servicio_id: int, activo: bool, db: Session = Depends(get_db)):
    """Publica o despublica un servicio sin borrarlo. Ruta PROTEGIDA para admin y empleado."""
    servicio = db.get(Servicio, servicio_id)
    if servicio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado.")

    servicio.activo = activo
    db.commit()

    return {
        "mensaje": "Servicio publicado correctamente." if activo else "Servicio despublicado correctamente.",
        "activo": activo,
    }


@router.delete(
    "/{servicio_id}",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin"))],
)
def eliminar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    """Elimina un servicio. Ruta PROTEGIDA solo para admin."""
    servicio = db.get(Servicio, servicio_id)
    if servicio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado.")

    db.delete(servicio)
    db.commit()

    return {"mensaje": "Servicio eliminado correctamente."}

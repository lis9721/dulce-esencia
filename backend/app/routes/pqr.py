"""
Router de /api/pqr (Quinto Avance — requerimiento 16).

El cliente crea su PQR y consulta el estado de las suyas.
Admin/empleado ven y gestionan todas (cambian estado, responden).
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, requiere_rol
from app.database import get_db
from app.models.pqr import PQR, EstadoPQR
from app.models.usuario import Usuario
from app.schemas.pqr import PQRActualizar, PQRCrear, PQRSalida
from app.services.notificaciones import notificar_pqr_recibida
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

router = APIRouter(prefix="/api/pqr", tags=["pqr"])


@router.post("", response_model=PQRSalida, status_code=status.HTTP_201_CREATED)
def crear_pqr(
    datos: PQRCrear,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Registra una PQR para el usuario autenticado. Ruta PROTEGIDA: cualquier usuario con sesión.

    El correo de confirmación se envía como TAREA EN SEGUNDO PLANO
    (`BackgroundTasks`): la respuesta 201 sale de inmediato y el envío
    corre después, sin bloquear ni romper la creación si el SMTP falla.
    """
    pqr = PQR(
        cliente_id=usuario.id,
        tipo=datos.tipo,
        asunto=datos.asunto,
        descripcion=datos.descripcion,
        estado=EstadoPQR.pendiente,
    )
    db.add(pqr)
    db.commit()
    db.refresh(pqr)

    background_tasks.add_task(
        notificar_pqr_recibida, usuario.correo, usuario.nombre, pqr.id, pqr.tipo.value, pqr.asunto
    )
    return pqr


@router.get("", response_model=None)
def listar_pqr(
    estado: EstadoPQR | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Lista PQR. Un `cliente` solo ve las suyas; `admin`/`empleado` ven
    todas (con filtro opcional por estado, para la bandeja de gestión).
    """
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit)

    consulta = db.query(PQR)
    if usuario.rol not in ("admin", "empleado"):
        consulta = consulta.filter(PQR.cliente_id == usuario.id)
    if estado is not None:
        consulta = consulta.filter(PQR.estado == estado)

    total = consulta.count()
    resultados = consulta.order_by(PQR.id.desc()).offset(offset).limit(limite_final).all()

    return {
        "datos": [PQRSalida.model_validate(p) for p in resultados],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get("/{pqr_id}", response_model=PQRSalida)
def obtener_pqr(pqr_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    pqr = db.get(PQR, pqr_id)
    if pqr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PQR no encontrada.")
    if pqr.cliente_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver esta PQR.")
    return pqr


@router.patch(
    "/{pqr_id}",
    response_model=PQRSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def gestionar_pqr(
    pqr_id: int,
    datos: PQRActualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Cambia el estado y/o agrega la respuesta de una PQR. Ruta PROTEGIDA: admin/empleado."""
    pqr = db.get(PQR, pqr_id)
    if pqr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PQR no encontrada.")

    if datos.respuesta is not None:
        pqr.respuesta = datos.respuesta
        pqr.respondido_por_id = usuario.id
        if datos.estado is None:
            pqr.estado = EstadoPQR.respondida
    if datos.estado is not None:
        pqr.estado = datos.estado

    db.commit()
    db.refresh(pqr)
    return pqr

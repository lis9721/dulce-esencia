"""
Router de /api/contacto.

POST es público (el formulario de contacto de la página, sin login);
GET/DELETE son de gestión, para que admin/empleado revisen la
bandeja de mensajes recibidos.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import requiere_rol
from app.database import get_db
from app.models.contacto import MensajeContacto
from app.schemas.contacto import ContactoCrear, ContactoSalida
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

router = APIRouter(prefix="/api/contacto", tags=["contacto"])


@router.post("", response_model=ContactoSalida, status_code=status.HTTP_201_CREATED)
def enviar_mensaje(datos: ContactoCrear, db: Session = Depends(get_db)):
    """Recibe un mensaje del formulario de contacto. Ruta PÚBLICA."""
    mensaje = MensajeContacto(**datos.model_dump())
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)
    return mensaje


@router.get("", response_model=None, dependencies=[Depends(requiere_rol("admin", "empleado"))])
def listar_mensajes(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Lista los mensajes de contacto recibidos, paginados, del más reciente al más antiguo. Ruta PROTEGIDA para admin y empleado."""
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    total = db.query(MensajeContacto).count()
    mensajes = (
        db.query(MensajeContacto)
        .order_by(MensajeContacto.id.desc())
        .offset(offset)
        .limit(limite_final)
        .all()
    )

    return {
        "datos": [ContactoSalida.model_validate(m) for m in mensajes],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get(
    "/{mensaje_id}",
    response_model=ContactoSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def obtener_mensaje(mensaje_id: int, db: Session = Depends(get_db)):
    """Detalle de un mensaje de contacto. Ruta PROTEGIDA para admin y empleado."""
    mensaje = db.get(MensajeContacto, mensaje_id)
    if mensaje is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensaje no encontrado.")
    return mensaje


@router.delete(
    "/{mensaje_id}",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def eliminar_mensaje(mensaje_id: int, db: Session = Depends(get_db)):
    """Elimina un mensaje de contacto ya atendido. Ruta PROTEGIDA para admin y empleado."""
    mensaje = db.get(MensajeContacto, mensaje_id)
    if mensaje is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensaje no encontrado.")

    db.delete(mensaje)
    db.commit()

    return {"mensaje": "Mensaje eliminado correctamente."}

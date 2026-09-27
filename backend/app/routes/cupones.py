"""
Router de /api/cupones.

Gestión de cupones (protegida, GestionCupones.jsx) + un endpoint
autenticado de validación para previsualizar el descuento en el
carrito antes de confirmar el pedido.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user, requiere_rol
from app.database import get_db
from app.models.cupon import Cupon
from app.models.usuario import Usuario
from app.rate_limit import LIMITE_CUPON, MENSAJE_LIMITE_CUPON, limiter
from app.schemas.cupon import (
    CuponActualizar,
    CuponCrear,
    CuponEstadoEntrada,
    CuponSalida,
    CuponValidarEntrada,
    CuponValidarSalida,
)
from app.utils.cupones import CuponInvalido, buscar_cupon_aplicable, calcular_descuento
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

router = APIRouter(prefix="/api/cupones", tags=["cupones"])


@router.post("/validar", response_model=CuponValidarSalida)
@limiter.limit(LIMITE_CUPON, error_message=MENSAJE_LIMITE_CUPON)
def validar_cupon(
    request: Request,
    datos: CuponValidarEntrada,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Ruta AUTENTICADA (cualquier rol, igual que en Node): previsualiza
    si un código de cupón es aplicable a un subtotal dado y qué
    descuento daría, SIN gastar uno de sus usos (eso solo ocurre al
    confirmar la compra en POST /api/pedidos).

    `usuario` no se usa en el cuerpo de la función — solo exige que
    haya sesión iniciada, exactamente como `verificarToken` delante de
    `limiterCupon` en cupones.routes.js. Esto cierra la brecha de
    paridad con Node (antes esta ruta era pública). El frontend ya
    estaba preparado para esto: `Carrito.jsx` solo renderiza el campo
    de cupón cuando `!esInvitado`, así que no requiere ningún cambio.
    """
    try:
        cupon = buscar_cupon_aplicable(db, datos.codigo, datos.subtotal)
    except CuponInvalido as error:
        return CuponValidarSalida(
            valido=False,
            codigo=datos.codigo,
            descuento=0,
            total=datos.subtotal,
            mensaje=error.mensaje,
        )

    descuento = calcular_descuento(cupon, datos.subtotal)
    return CuponValidarSalida(
        valido=True,
        codigo=cupon.codigo,
        descuento=descuento,
        total=round(datos.subtotal - descuento, 2),
        mensaje="Cupón aplicado correctamente.",
    )


@router.get("", response_model=None, dependencies=[Depends(requiere_rol("admin", "empleado"))])
def listar_cupones(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Lista los cupones, paginados. Ruta PROTEGIDA para admin y empleado."""
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    total = db.query(Cupon).count()
    cupones = (
        db.query(Cupon).order_by(Cupon.id.desc()).offset(offset).limit(limite_final).all()
    )

    return {
        "datos": [CuponSalida.model_validate(c) for c in cupones],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get(
    "/{cupon_id}",
    response_model=CuponSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def obtener_cupon(cupon_id: int, db: Session = Depends(get_db)):
    """Detalle de un cupón por id. Ruta PROTEGIDA para admin y empleado."""
    cupon = db.get(Cupon, cupon_id)
    if cupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupón no encontrado.")
    return cupon


@router.post(
    "",
    response_model=CuponSalida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_rol("admin"))],
)
def crear_cupon(datos: CuponCrear, db: Session = Depends(get_db)):
    """Crea un cupón nuevo. Ruta PROTEGIDA solo para admin."""
    cupon = Cupon(**datos.model_dump())
    db.add(cupon)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cupón con ese código.",
        ) from None
    db.refresh(cupon)
    return cupon


@router.put(
    "/{cupon_id}",
    response_model=CuponSalida,
    dependencies=[Depends(requiere_rol("admin"))],
)
def actualizar_cupon(cupon_id: int, datos: CuponActualizar, db: Session = Depends(get_db)):
    """Reemplaza todos los campos editables de un cupón (usos_actuales NO es editable aquí: solo lo mueve el checkout). Ruta PROTEGIDA solo para admin."""
    cupon = db.get(Cupon, cupon_id)
    if cupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupón no encontrado.")

    for campo, valor in datos.model_dump().items():
        setattr(cupon, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cupón con ese código.",
        ) from None
    db.refresh(cupon)
    return cupon


@router.patch(
    "/{cupon_id}/estado",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin"))],
)
def cambiar_estado_cupon(cupon_id: int, datos: CuponEstadoEntrada, db: Session = Depends(get_db)):
    """Activa o desactiva un cupón sin borrarlo. Ruta PROTEGIDA solo para admin."""
    cupon = db.get(Cupon, cupon_id)
    if cupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupón no encontrado.")

    cupon.activo = datos.activo
    db.commit()

    return {
        "mensaje": "Cupón activado correctamente." if datos.activo else "Cupón desactivado correctamente.",
        "activo": datos.activo,
    }


@router.delete(
    "/{cupon_id}",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin"))],
)
def eliminar_cupon(cupon_id: int, db: Session = Depends(get_db)):
    """Elimina un cupón. Ruta PROTEGIDA solo para admin. Los pedidos ya hechos con este cupón conservan `pedidos.cupon_codigo` como texto plano, así que borrarlo no rompe el historial."""
    cupon = db.get(Cupon, cupon_id)
    if cupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupón no encontrado.")

    db.delete(cupon)
    db.commit()

    return {"mensaje": "Cupón eliminado correctamente."}

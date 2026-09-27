"""
Reseñas y calificaciones de productos ("compra verificada").

Solo puede reseñar un producto quien tiene al menos un pedido en
estado `pagado` o `entregado` que lo incluya (_validar_compra) — no
cualquiera que abra la página. Cada usuario puede dejar una sola
reseña por producto (UniqueConstraint en el modelo); para cambiar de
opinión, la edita (PUT) o la borra (DELETE) en vez de acumular varias.

`Producto.calificacion_promedio`/`total_resenas` son denormalizados y
se recalculan aquí mismo (_recalcular_agregado) cada vez que una
reseña se crea, edita o borra — así el catálogo público nunca necesita
una subconsulta de agregación por producto solo para mostrar estrellas.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.pedido import EstadoPedido, Pedido, PedidoItem
from app.models.producto import Producto
from app.models.resena import Resena
from app.models.usuario import Usuario
from app.schemas.resena import ResenaCrear, ResenaSalida
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

router = APIRouter(prefix="/api/productos/{producto_id}/resenas", tags=["reseñas"])


def _obtener_producto_o_404(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")
    return producto


def _validar_compra(db: Session, usuario_id: int, producto_id: int) -> None:
    """
    "Compra verificada": exige `pagado` o `entregado` (no basta con
    `pendiente`, que puede ser un pedido contraentrega que ni siquiera
    se ha cobrado todavía). No se exige específicamente `entregado`
    para no depender de que el admin/empleado haya marcado el pedido a
    mano — ver la nota del módulo.
    """
    existe = (
        db.query(PedidoItem.id)
        .join(Pedido, Pedido.id == PedidoItem.pedido_id)
        .filter(
            Pedido.usuario_id == usuario_id,
            PedidoItem.producto_id == producto_id,
            Pedido.estado.in_([EstadoPedido.pagado, EstadoPedido.entregado]),
        )
        .first()
    )
    if existe is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes reseñar productos que hayas comprado y pagado.",
        )


def _recalcular_agregado(db: Session, producto: Producto) -> None:
    promedio, total = (
        db.query(func.avg(Resena.calificacion), func.count(Resena.id)).filter(Resena.producto_id == producto.id).one()
    )
    producto.calificacion_promedio = round(float(promedio), 1) if promedio is not None else 0
    producto.total_resenas = total or 0


@router.get("", response_model=None)
def listar_resenas(
    producto_id: int,
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Listado público y paginado — no requiere autenticación."""
    _obtener_producto_o_404(db, producto_id)
    pagina, limite, offset = obtener_parametros_paginacion(page, limit)

    consulta = (
        db.query(Resena)
        .options(joinedload(Resena.usuario))
        .filter(Resena.producto_id == producto_id)
        .order_by(Resena.creado_en.desc())
    )
    total = consulta.count()
    resenas = consulta.offset(offset).limit(limite).all()

    return {
        "datos": [ResenaSalida.model_validate(r) for r in resenas],
        "meta": construir_meta_paginacion(pagina, limite, total),
    }


@router.post("", response_model=ResenaSalida, status_code=status.HTTP_201_CREATED)
def crear_resena(
    producto_id: int,
    datos: ResenaCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    producto = _obtener_producto_o_404(db, producto_id)
    _validar_compra(db, usuario.id, producto_id)

    ya_existe = (
        db.query(Resena.id).filter(Resena.producto_id == producto_id, Resena.usuario_id == usuario.id).first()
    )
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya reseñaste este producto. Edita tu reseña existente en vez de crear otra.",
        )

    resena = Resena(
        producto_id=producto_id,
        usuario_id=usuario.id,
        calificacion=datos.calificacion,
        comentario=datos.comentario,
    )
    db.add(resena)
    db.flush()
    _recalcular_agregado(db, producto)
    db.commit()
    db.refresh(resena)
    return resena


@router.put("/{resena_id}", response_model=ResenaSalida)
def editar_resena(
    producto_id: int,
    resena_id: int,
    datos: ResenaCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    producto = _obtener_producto_o_404(db, producto_id)
    resena = db.get(Resena, resena_id)
    if resena is None or resena.producto_id != producto_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada.")
    if resena.usuario_id != usuario.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes editar tu propia reseña.")

    resena.calificacion = datos.calificacion
    resena.comentario = datos.comentario
    db.flush()
    _recalcular_agregado(db, producto)
    db.commit()
    db.refresh(resena)
    return resena


@router.delete("/{resena_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_resena(
    producto_id: int,
    resena_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """El propio autor puede borrar su reseña; admin/empleado puede borrar cualquiera (moderación de contenido ofensivo)."""
    producto = _obtener_producto_o_404(db, producto_id)
    resena = db.get(Resena, resena_id)
    if resena is None or resena.producto_id != producto_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada.")
    if resena.usuario_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para borrar esta reseña.")

    db.delete(resena)
    db.flush()
    _recalcular_agregado(db, producto)
    db.commit()

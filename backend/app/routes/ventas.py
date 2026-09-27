"""
Router de /api/ventas (Quinto Avance — módulo de gestión comercial).

POST /api/ventas registra una venta directa de punto de venta (solo
admin/empleado): productos y/o servicios, cantidades y precios se
resuelven SIEMPRE contra el catálogo real en la base de datos, nunca
contra lo que mande el cliente HTTP — mismo criterio que el checkout
de pedidos (app/routes/pedidos.py).

POST /api/ventas/desde-pedido/{pedido_id} genera una venta a partir de
un Pedido del sitio web ya `pagado`, sin volver a pedir los ítems (se
copian del pedido) — así las compras normales del sitio también entran
al historial de ventas/reportes/dashboards sin que el cliente tenga que
hacer nada extra.
"""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user, requiere_rol
from app.database import get_db
from app.models.pedido import Pedido
from app.models.producto import Producto
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.models.venta import DetalleVenta, EstadoVenta, Venta
from app.schemas.venta import VentaCrear, VentaEstadoEntrada, VentaSalida
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

router = APIRouter(prefix="/api/ventas", tags=["ventas"])


def _cargar_venta(db: Session, venta_id: int) -> Venta | None:
    return (
        db.query(Venta)
        .options(joinedload(Venta.items))
        .filter(Venta.id == venta_id)
        .first()
    )


@router.post(
    "",
    response_model=VentaSalida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def registrar_venta(
    datos: VentaCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Registra una venta de punto de venta. Ruta PROTEGIDA: solo admin/empleado."""
    cliente = db.get(Usuario, datos.cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El cliente indicado no existe.")

    subtotal = 0.0
    items_a_crear = []
    for item in datos.items:
        if item.producto_id:
            producto = db.get(Producto, item.producto_id)
            if producto is None or not producto.activo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"El producto {item.producto_id} no existe o no está activo."
                )
            if producto.stock < item.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Solo quedan {producto.stock} unidades de '{producto.titulo}'.",
                )
            precio = float(producto.precio)
            nombre = producto.titulo
            producto.stock -= item.cantidad
            items_a_crear.append(
                {"producto_id": producto.id, "servicio_id": None, "nombre": nombre, "precio": precio, "cantidad": item.cantidad}
            )
        else:
            servicio = db.get(Servicio, item.servicio_id)
            if servicio is None or not servicio.activo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El servicio {item.servicio_id} no existe o no está activo.",
                )
            precio = float(servicio.precio)
            nombre = servicio.nombre
            items_a_crear.append(
                {"producto_id": None, "servicio_id": servicio.id, "nombre": nombre, "precio": precio, "cantidad": item.cantidad}
            )
        subtotal += precio * item.cantidad

    subtotal = round(subtotal, 2)
    descuento = round(datos.descuento, 2)
    impuestos = round(datos.impuestos, 2)
    if descuento > subtotal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El descuento no puede ser mayor al subtotal.")
    total = round(subtotal - descuento + impuestos, 2)

    venta = Venta(
        cliente_id=cliente.id,
        vendedor_id=usuario.id,
        subtotal=subtotal,
        descuento=descuento,
        impuestos=impuestos,
        total=total,
        estado=EstadoVenta.completada,
        notas=datos.notas,
    )
    db.add(venta)
    db.flush()

    for item in items_a_crear:
        db.add(
            DetalleVenta(
                venta_id=venta.id,
                producto_id=item["producto_id"],
                servicio_id=item["servicio_id"],
                nombre=item["nombre"],
                precio_unitario=item["precio"],
                cantidad=item["cantidad"],
                subtotal=round(item["precio"] * item["cantidad"], 2),
            )
        )

    db.commit()
    db.refresh(venta)
    return venta


@router.post(
    "/desde-pedido/{pedido_id}",
    response_model=VentaSalida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def generar_venta_desde_pedido(pedido_id: int, db: Session = Depends(get_db)):
    """
    Genera (o devuelve, si ya existía) la venta correspondiente a un
    pedido del sitio web. El pedido debe estar `pagado` (o en un
    estado posterior) — no tiene sentido registrar como venta algo que
    todavía no se cobró. Ruta PROTEGIDA: admin/empleado.
    """
    pedido = db.query(Pedido).options(joinedload(Pedido.items)).filter(Pedido.id == pedido_id).first()
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El pedido no existe.")

    venta_existente = db.query(Venta).filter(Venta.pedido_id == pedido.id).first()
    if venta_existente is not None:
        return _cargar_venta(db, venta_existente.id)

    if pedido.estado.value not in ("pagado", "enviado", "entregado"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pedido debe estar pagado para poder generar la venta correspondiente.",
        )

    venta = Venta(
        cliente_id=pedido.usuario_id,
        vendedor_id=None,
        pedido_id=pedido.id,
        subtotal=pedido.subtotal,
        descuento=pedido.descuento,
        impuestos=0,
        total=pedido.total,
        estado=EstadoVenta.completada,
        notas=f"Generada automáticamente desde el pedido #{pedido.id} del sitio web.",
    )
    db.add(venta)
    db.flush()

    for item in pedido.items:
        db.add(
            DetalleVenta(
                venta_id=venta.id,
                producto_id=item.producto_id,
                servicio_id=None,
                nombre=item.titulo,
                precio_unitario=item.precio_unitario,
                cantidad=item.cantidad,
                subtotal=round(float(item.precio_unitario) * item.cantidad, 2),
            )
        )

    db.commit()
    db.refresh(venta)
    return venta


@router.get("", response_model=None)
def historial_ventas(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    cliente_id: int | None = Query(default=None),
    producto_id: int | None = Query(default=None),
    servicio_id: int | None = Query(default=None),
    estado: EstadoVenta | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Historial de ventas con filtros (requerimiento 3). Un `cliente`
    solo ve SUS propias ventas; `admin`/`empleado` ven las de todos.
    """
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit)

    consulta = db.query(Venta).options(joinedload(Venta.items))
    if usuario.rol not in ("admin", "empleado"):
        consulta = consulta.filter(Venta.cliente_id == usuario.id)
    elif cliente_id is not None:
        consulta = consulta.filter(Venta.cliente_id == cliente_id)

    if fecha_inicio is not None:
        consulta = consulta.filter(Venta.creado_en >= datetime.combine(fecha_inicio, time.min))
    if fecha_fin is not None:
        consulta = consulta.filter(Venta.creado_en <= datetime.combine(fecha_fin, time.max))
    if estado is not None:
        consulta = consulta.filter(Venta.estado == estado)
    if producto_id is not None:
        consulta = consulta.filter(
            Venta.id.in_(db.query(DetalleVenta.venta_id).filter(DetalleVenta.producto_id == producto_id))
        )
    if servicio_id is not None:
        consulta = consulta.filter(
            Venta.id.in_(db.query(DetalleVenta.venta_id).filter(DetalleVenta.servicio_id == servicio_id))
        )

    total = consulta.count()
    ventas = consulta.order_by(Venta.id.desc()).offset(offset).limit(limite_final).all()

    return {
        "datos": [VentaSalida.model_validate(v) for v in ventas],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get("/{venta_id}", response_model=VentaSalida)
def obtener_venta(venta_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Detalle de una venta. Ruta PROTEGIDA: solo el cliente dueño o admin/empleado."""
    venta = _cargar_venta(db, venta_id)
    if venta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada.")
    if venta.cliente_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver esta venta.")
    return venta


@router.patch(
    "/{venta_id}/estado",
    response_model=VentaSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def cambiar_estado_venta(venta_id: int, datos: VentaEstadoEntrada, db: Session = Depends(get_db)):
    """Cambia el estado de una venta (completada/anulada). Ruta PROTEGIDA: admin/empleado."""
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada.")
    venta.estado = datos.estado
    db.commit()
    db.refresh(venta)
    return venta

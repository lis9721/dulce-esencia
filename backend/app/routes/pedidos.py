"""
Router de /api/pedidos.

POST /api/pedidos es el checkout: arma el pedido a partir del
CARRITO REAL del usuario (nunca de una lista de productos que mande
el cliente HTTP), vuelve a validar stock y precio en el servidor,
descuenta el stock, congela los datos de cada ítem comprado y vacía
el carrito — todo dentro de una sola transacción de base de datos.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user, requiere_rol
from app.config import get_settings
from app.database import get_db
from app.exceptions.pagos import ProveedorPagoException
from app.models.carrito import Carrito, CarritoItem
from app.models.pago import EstadoPago, Pago
from app.models.pedido import EstadoPedido, Pedido, PedidoItem, TipoEntrega
from app.models.usuario import Usuario
from app.schemas.pedido import PedidoCrear, PedidoEstadoEntrada, PedidoSalida
from app.services.notificaciones import (
    notificar_pedido_cambio_estado,
    notificar_pedido_cancelado,
    notificar_pedido_confirmado,
)
from app.services.pagos.payment_factory import obtener_proveedor
from app.services.pagos.transiciones import transicionar_estado
from app.utils.cupones import CuponInvalido, buscar_cupon_aplicable, calcular_descuento
from app.utils.factura import generar_pdf_factura
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

router = APIRouter(prefix="/api/pedidos", tags=["pedidos"])

# Texto fijo que se guarda en `direccion_envio` cuando tipo_entrega es
# "recoger_tienda" — la columna sigue siendo NOT NULL a propósito (ver
# app/models/pedido.py), así que necesita SIEMPRE un valor, y este deja
# claro en la factura/panel que no es una dirección real de envío.
DIRECCION_RECOGER_EN_TIENDA = "Recoge en tienda — Dulce Esencia Pastelería"


@router.post("", response_model=PedidoSalida, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    datos: PedidoCrear,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Confirma el pedido (checkout) a partir del carrito actual del
    usuario autenticado. Ruta PROTEGIDA (cualquier usuario logueado).

    Idempotencia: si `idempotency_key` viene en el body y ya existe un
    pedido de este usuario con esa misma clave, se devuelve ESE pedido
    tal cual en vez de crear uno nuevo (evita doble cobro por un
    reintento de red o un doble clic en "Confirmar compra").
    """
    if datos.idempotency_key:
        pedido_existente = (
            db.query(Pedido)
            .options(joinedload(Pedido.items))
            .filter(Pedido.usuario_id == usuario.id, Pedido.idempotency_key == datos.idempotency_key)
            .first()
        )
        if pedido_existente is not None:
            return pedido_existente

    carrito = db.query(Carrito).filter(Carrito.usuario_id == usuario.id).first()
    items_carrito = (
        db.query(CarritoItem)
        .options(joinedload(CarritoItem.producto))
        .filter(CarritoItem.carrito_id == carrito.id)
        .all()
        if carrito is not None
        else []
    )
    if not items_carrito:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tu carrito está vacío.")

    # Se revalida stock/estado de CADA producto con los datos actuales
    # de la base de datos antes de cobrar nada — el precio y el stock
    # que "cree" tener el navegador nunca son la fuente de verdad.
    subtotal = 0.0
    for item in items_carrito:
        producto = item.producto
        if not producto.activo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{producto.titulo}' ya no está disponible. Quítalo del carrito para continuar.",
            )
        if producto.stock < item.cantidad:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Solo quedan {producto.stock} unidades de '{producto.titulo}'.",
            )
        subtotal += float(producto.precio) * item.cantidad
    subtotal = round(subtotal, 2)

    descuento = 0.0
    cupon = None
    if datos.cupon_codigo:
        try:
            cupon = buscar_cupon_aplicable(db, datos.cupon_codigo, subtotal)
        except CuponInvalido as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.mensaje) from None
        descuento = calcular_descuento(cupon, subtotal)

    total = round(subtotal - descuento, 2)

    pedido = Pedido(
        usuario_id=usuario.id,
        subtotal=subtotal,
        descuento=descuento,
        cupon_codigo=cupon.codigo if cupon else None,
        total=total,
        direccion_envio=(
            datos.direccion_envio if datos.tipo_entrega == TipoEntrega.domicilio else DIRECCION_RECOGER_EN_TIENDA
        ),
        telefono_contacto=datos.telefono_contacto,
        metodo_pago=datos.metodo_pago,
        tipo_entrega=datos.tipo_entrega,
        fecha_entrega_solicitada=datos.fecha_entrega_solicitada,
        franja_horaria=datos.franja_horaria,
        idempotency_key=datos.idempotency_key,
    )
    db.add(pedido)
    db.flush()  # asigna pedido.id sin cerrar la transacción todavía

    for item in items_carrito:
        producto = item.producto
        db.add(
            PedidoItem(
                pedido_id=pedido.id,
                producto_id=producto.id,
                titulo=producto.titulo,
                precio_unitario=producto.precio,
                cantidad=item.cantidad,
            )
        )
        producto.stock -= item.cantidad

    if cupon is not None:
        cupon.usos_actuales += 1

    db.query(CarritoItem).filter(CarritoItem.carrito_id == carrito.id).delete()

    db.commit()
    db.refresh(pedido)

    background_tasks.add_task(
        notificar_pedido_confirmado,
        usuario.correo,
        usuario.nombre,
        pedido.id,
        float(pedido.total),
        pedido.tipo_entrega.value,
        pedido.fecha_entrega_solicitada.isoformat() if pedido.fecha_entrega_solicitada else None,
        pedido.franja_horaria,
    )
    return pedido


@router.get("", response_model=None)
def listar_pedidos(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Lista pedidos, paginados. Ruta PROTEGIDA: un `cliente` solo ve SUS
    propios pedidos; `admin`/`empleado` ven los de todos los usuarios
    (equivalente al panel de administración de pedidos).
    """
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    consulta = db.query(Pedido)
    if usuario.rol not in ("admin", "empleado"):
        consulta = consulta.filter(Pedido.usuario_id == usuario.id)

    total = consulta.count()
    pedidos = consulta.order_by(Pedido.id.desc()).offset(offset).limit(limite_final).all()

    return {
        "datos": [PedidoSalida.model_validate(p) for p in pedidos],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get("/{pedido_id}", response_model=PedidoSalida)
def obtener_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Detalle de un pedido. Ruta PROTEGIDA: solo su dueño o admin/empleado pueden verlo."""
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")

    if pedido.usuario_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este pedido.")

    return pedido


@router.get("/{pedido_id}/factura")
def descargar_factura_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Genera y devuelve el PDF de la factura del pedido `pedido_id`, al
    vuelo (no se guarda en disco: se recalcula desde `pedidos` +
    `pedido_items` + `usuarios` en cada petición). Misma autorización a
    nivel de fila que GET /api/pedidos/{pedido_id}: solo el dueño del
    pedido o admin/empleado. Réplica de GET /api/pedidos/:id/factura en
    pedidos.routes.js (ahí con pdfkit; acá con reportlab — ver
    app/utils/factura.py).

    Antes de este cambio esta ruta no existía en el backend Python: el
    botón "descargar factura" del frontend (MisPedidos.jsx,
    PedidoDetalle.jsx) daba 404.
    """
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El pedido no existe.")

    if pedido.usuario_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este pedido.")

    # No debería pasar (FOREIGN KEY usuario_id -> usuarios.id), pero si
    # el usuario fue eliminado igual se falla explícito en vez de
    # generar una factura con datos de cliente vacíos — mismo criterio
    # que la versión Node.
    cliente = pedido.usuario
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron los datos del cliente del pedido."
        )

    buffer = generar_pdf_factura(pedido, cliente)
    nombre_archivo = f"factura-pedido-{pedido.id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def cambiar_estado_pedido(
    pedido_id: int,
    datos: PedidoEstadoEntrada,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Actualiza el estado de un pedido (pendiente → pagado → enviado → entregado). Ruta PROTEGIDA para admin y empleado."""
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")

    if datos.estado == EstadoPedido.cancelado:
        # Cancelar por aquí se saltaría el reembolso automático y la
        # devolución de stock — para eso está el endpoint dedicado.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para cancelar un pedido usa POST /api/pedidos/{id}/cancelar (reembolsa el pago y repone el stock).",
        )
    if pedido.estado == EstadoPedido.cancelado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este pedido ya está cancelado.")

    estado_anterior = pedido.estado
    pedido.estado = datos.estado
    db.commit()
    db.refresh(pedido)

    if pedido.estado != estado_anterior:
        cliente = pedido.usuario
        if cliente is not None:
            background_tasks.add_task(
                notificar_pedido_cambio_estado, cliente.correo, cliente.nombre, pedido.id, pedido.estado.value
            )
    return pedido


@router.post("/{pedido_id}/cancelar", response_model=PedidoSalida)
def cancelar_pedido(
    pedido_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Cancela un pedido propio (o de cualquier usuario, si quien pide es
    admin/empleado) que todavía esté `pendiente` o `pagado`:

      1. Si tiene un pago APROBADO asociado, lo reembolsa en Wompi
         (`refund_payment` — ver WompiProvider) ANTES de marcar nada
         como cancelado: si el reembolso falla, el pedido se queda
         como estaba y se devuelve 502, nunca queda "cancelado" con
         plata del cliente todavía retenida sin haberlo intentado.
      2. Repone el stock de cada ítem (el checkout lo descuenta al
         crear el pedido, sin importar el método de pago).
      3. Notifica por correo, incluyendo si hubo o no reembolso.

    Pedidos ya `enviado`/`entregado`/`cancelado` no se pueden cancelar
    por aquí (un pedido ya entregado es una devolución, no una
    cancelación — un flujo distinto que este proyecto no cubre todavía).
    """
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")

    if pedido.usuario_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para cancelar este pedido.")

    if pedido.estado not in (EstadoPedido.pendiente, EstadoPedido.pagado):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un pedido en estado '{pedido.estado.value}' ya no se puede cancelar por aquí.",
        )

    pago = (
        db.query(Pago)
        .filter(Pago.pedido_id == pedido.id)
        .order_by(Pago.id.desc())
        .first()
    )
    hubo_reembolso = False
    if pago is not None and pago.estado == EstadoPago.APPROVED:
        proveedor = obtener_proveedor(pago.proveedor, get_settings())
        try:
            resultado = proveedor.refund_payment(pago.id_transaccion_proveedor)
        except ProveedorPagoException:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No fue posible procesar el reembolso con el proveedor de pago. Intenta de nuevo más tarde.",
            ) from None
        pago.estado = transicionar_estado(pago.estado, resultado.estado)
        pago.respuesta_cruda = resultado.respuesta_cruda
        db.add(pago)
        hubo_reembolso = pago.estado == EstadoPago.VOIDED

    for item in pedido.items:
        producto = item.producto
        if producto is not None:
            producto.stock += item.cantidad

    pedido.estado = EstadoPedido.cancelado
    db.commit()
    db.refresh(pedido)

    cliente = pedido.usuario
    if cliente is not None:
        background_tasks.add_task(notificar_pedido_cancelado, cliente.correo, cliente.nombre, pedido.id, hubo_reembolso)
    return pedido

"""
Router de /api/carrito.

El carrito es siempre "el carrito del usuario que hace la petición":
no existe un `carrito_id` en la URL, se resuelve internamente a
partir de `get_current_user`. Se crea de forma perezosa (lazy) la
primera vez que el usuario agrega un ítem — no hace falta un POST
/api/carrito separado para "abrir" un carrito.

Disponible para cualquier usuario autenticado (no se restringe a
`cliente`): un admin o empleado que también compre en la tienda usa
el mismo flujo.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.carrito import Carrito, CarritoItem
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.schemas.carrito import (
    CarritoFusionarEntrada,
    CarritoItemActualizar,
    CarritoItemEntrada,
    CarritoItemSalida,
    CarritoSalida,
)

router = APIRouter(prefix="/api/carrito", tags=["carrito"])


def _obtener_o_crear_carrito(db: Session, usuario: Usuario) -> Carrito:
    """Devuelve el carrito del usuario, creándolo vacío si es la primera vez."""
    carrito = db.query(Carrito).filter(Carrito.usuario_id == usuario.id).first()
    if carrito is None:
        carrito = Carrito(usuario_id=usuario.id)
        db.add(carrito)
        db.commit()
        db.refresh(carrito)
    return carrito


def _serializar_carrito(db: Session, carrito: Carrito) -> CarritoSalida:
    """Arma la salida del carrito enriqueciendo cada ítem con los datos ACTUALES del producto (no los del momento en que se agregó)."""
    items_orm = (
        db.query(CarritoItem)
        .options(joinedload(CarritoItem.producto))
        .filter(CarritoItem.carrito_id == carrito.id)
        .order_by(CarritoItem.id.asc())
        .all()
    )

    items_salida: list[CarritoItemSalida] = []
    total = 0.0
    for item in items_orm:
        producto = item.producto
        subtotal = float(producto.precio) * item.cantidad
        total += subtotal
        items_salida.append(
            CarritoItemSalida(
                producto_id=producto.id,
                titulo=producto.titulo,
                imagen=producto.imagen,
                precio=float(producto.precio),
                stock_disponible=producto.stock,
                cantidad=item.cantidad,
                subtotal=subtotal,
                agregado_en=item.agregado_en,
            )
        )

    return CarritoSalida(items=items_salida, total=total, cantidad_items=sum(i.cantidad for i in items_orm))


def _validar_producto_disponible(db: Session, producto_id: int, cantidad: int) -> Producto:
    """Un producto solo se puede agregar/actualizar en el carrito si existe, está publicado y tiene stock suficiente."""
    producto = db.get(Producto, producto_id)
    if producto is None or not producto.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado o no disponible.")
    if producto.stock < cantidad:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Solo quedan {producto.stock} unidades disponibles de '{producto.titulo}'.",
        )
    return producto


@router.get("", response_model=CarritoSalida)
def ver_carrito(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Muestra el carrito del usuario autenticado, con totales ya calculados."""
    carrito = _obtener_o_crear_carrito(db, usuario)
    return _serializar_carrito(db, carrito)


@router.post("/items", response_model=CarritoSalida, status_code=status.HTTP_201_CREATED)
def agregar_item(
    datos: CarritoItemEntrada,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Agrega un producto al carrito. Si el producto ya estaba en el
    carrito, SUMA la cantidad nueva a la que ya había (en vez de
    duplicar la fila, respetando el UniqueConstraint(carrito_id,
    producto_id) del modelo).
    """
    carrito = _obtener_o_crear_carrito(db, usuario)

    item_existente = (
        db.query(CarritoItem)
        .filter(CarritoItem.carrito_id == carrito.id, CarritoItem.producto_id == datos.producto_id)
        .first()
    )
    cantidad_final = datos.cantidad + (item_existente.cantidad if item_existente else 0)
    _validar_producto_disponible(db, datos.producto_id, cantidad_final)

    if item_existente is not None:
        item_existente.cantidad = cantidad_final
    else:
        db.add(CarritoItem(carrito_id=carrito.id, producto_id=datos.producto_id, cantidad=datos.cantidad))

    db.commit()
    return _serializar_carrito(db, carrito)


@router.put("/items/{producto_id}", response_model=CarritoSalida)
def actualizar_cantidad_item(
    producto_id: int,
    datos: CarritoItemActualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Fija la cantidad exacta de un producto ya presente en el carrito (a diferencia de POST /items, que suma)."""
    carrito = _obtener_o_crear_carrito(db, usuario)

    item = (
        db.query(CarritoItem)
        .filter(CarritoItem.carrito_id == carrito.id, CarritoItem.producto_id == producto_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ese producto no está en tu carrito.")

    _validar_producto_disponible(db, producto_id, datos.cantidad)
    item.cantidad = datos.cantidad
    db.commit()
    return _serializar_carrito(db, carrito)


@router.delete("/items/{producto_id}", response_model=CarritoSalida)
def quitar_item(
    producto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Quita un producto del carrito."""
    carrito = _obtener_o_crear_carrito(db, usuario)

    item = (
        db.query(CarritoItem)
        .filter(CarritoItem.carrito_id == carrito.id, CarritoItem.producto_id == producto_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ese producto no está en tu carrito.")

    db.delete(item)
    db.commit()
    return _serializar_carrito(db, carrito)


@router.delete("", response_model=CarritoSalida)
def vaciar_carrito(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Vacía el carrito por completo (ej. botón "vaciar carrito" en la UI), sin eliminar el carrito en sí."""
    carrito = _obtener_o_crear_carrito(db, usuario)
    db.query(CarritoItem).filter(CarritoItem.carrito_id == carrito.id).delete()
    db.commit()
    return _serializar_carrito(db, carrito)


@router.post("/fusionar", response_model=CarritoSalida)
def fusionar_carrito(
    datos: CarritoFusionarEntrada,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Fusiona el carrito de invitado (guardado en localStorage antes de
    iniciar sesión) con el que el usuario ya tuviera en la BD. Ruta
    PROTEGIDA (cualquier rol) — faltaba por completo: sin ella, un
    cliente que agregara productos al carrito ANTES de loguearse
    perdía esos ítems al iniciar sesión.

    A propósito NO reutiliza `_validar_producto_disponible` tal cual
    (que lanza 409 y aborta todo): a diferencia de agregar_item, aquí
    el usuario no está actuando sobre un ítem puntual, sino recibiendo
    de vuelta un carrito completo que armó en otro momento. Fallar la
    fusión ENTERA por un solo producto que mientras tanto se quedó sin
    stock o se despublicó sería peor experiencia que simplemente traer
    lo que sí se puede: cada ítem se omite si el producto ya no existe
    o no está publicado, y se limita al stock disponible en vez de
    rechazarse si pide más de lo que hay.
    """
    carrito = _obtener_o_crear_carrito(db, usuario)

    for item_entrada in datos.items:
        producto = db.get(Producto, item_entrada.producto_id)
        if producto is None or not producto.activo or producto.stock <= 0:
            continue

        item_existente = (
            db.query(CarritoItem)
            .filter(CarritoItem.carrito_id == carrito.id, CarritoItem.producto_id == item_entrada.producto_id)
            .first()
        )
        cantidad_previa = item_existente.cantidad if item_existente else 0
        cantidad_final = min(cantidad_previa + item_entrada.cantidad, producto.stock)

        if item_existente is not None:
            item_existente.cantidad = cantidad_final
        else:
            db.add(CarritoItem(carrito_id=carrito.id, producto_id=producto.id, cantidad=cantidad_final))

    db.commit()
    return _serializar_carrito(db, carrito)

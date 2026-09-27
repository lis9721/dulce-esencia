"""
Capa de acceso a datos de `productos` — el recurso principal del
proyecto (criterio 18: "El recurso principal implementa el CRUD
completo").

Esta es la ÚNICA capa que habla con la base de datos para este recurso
(criterio 9): el router de `app/routes/productos.py` ya no contiene
`db.query(...)`/`db.add(...)`/`db.commit(...)`, solo orquesta HTTP.

Reglas que se cumplen aquí (mismo criterio que app/crud/proveedores.py)
-------------------------------------------------------------------
  * 29 — ni una sola `HTTPException`: se lanzan las excepciones de
         dominio de `app/exceptions/dominio.py`; el handler global
         (`app/core/errores.py`) es el único que decide el código HTTP.
  * 50 — las consultas usan `select()`/`where()` y el conteo se resuelve
         en la base con `select(func.count())`, nunca `len()` sobre
         filas ya traídas a Python.
  * 52 — `IntegrityError` se captura, se hace `rollback()` y se traduce
         a `SkuDuplicado` (409), nunca se deja que la base reviente con
         un 500.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import proveedores as crud_proveedores
from app.exceptions.dominio import ProductoConPedidos, ProductoNoEncontrado, SkuDuplicado
from app.models.producto import FamiliaProducto, Producto
from app.utils.busqueda import CARACTER_ESCAPE, patron_contiene

# ----------------------------------------------------------------------
# Lectura
# ----------------------------------------------------------------------


def _consulta_filtrada(*, solo_activos: bool, familia: FamiliaProducto | None, buscar: str | None):
    """
    Arma el `select()` con los filtros opcionales del listado
    (criterio 22: paginación + filtros). Se comparte entre la consulta
    de datos y la de conteo para que el `total` de la paginación
    corresponda exactamente a los mismos filtros.
    """
    consulta = select(Producto)
    if solo_activos:
        consulta = consulta.where(Producto.activo.is_(True))
    if familia is not None:
        consulta = consulta.where(Producto.familia == familia)
    if buscar:
        # Parámetros vinculados vía ilike(), nunca concatenación de
        # texto (protección contra inyección SQL, igual que en
        # proveedores — ver docs/SEGURIDAD-SQL-INJECTION.md).
        consulta = consulta.where(Producto.titulo.ilike(patron_contiene(buscar), escape=CARACTER_ESCAPE))
    return consulta


def listar(
    db: Session,
    *,
    offset: int,
    limite: int,
    solo_activos: bool,
    familia: FamiliaProducto | None = None,
    buscar: str | None = None,
) -> tuple[list[Producto], int]:
    """Devuelve (página de productos, total que cumple los filtros)."""
    consulta = _consulta_filtrada(solo_activos=solo_activos, familia=familia, buscar=buscar)

    total = db.scalar(select(func.count()).select_from(consulta.order_by(None).subquery()))

    productos = (
        db.execute(consulta.order_by(Producto.orden.asc(), Producto.id.desc()).offset(offset).limit(limite))
        .scalars()
        .all()
    )
    return list(productos), int(total or 0)


def obtener_por_id(db: Session, producto_id: int) -> Producto:
    """Carga un producto o lanza `ProductoNoEncontrado` (nunca un 404 a mano)."""
    producto = db.scalar(select(Producto).where(Producto.id == producto_id))
    if producto is None:
        raise ProductoNoEncontrado(producto_id)
    return producto


def contar_pedidos(db: Session, producto_id: int) -> int:
    """
    Conteo resuelto en la base de datos. Import local para evitar un
    ciclo de imports entre `app.models.pedido` y `app.models.producto`.
    """
    from app.models.pedido import PedidoItem

    total = db.scalar(select(func.count(PedidoItem.id)).where(PedidoItem.producto_id == producto_id))
    return int(total or 0)


# ----------------------------------------------------------------------
# Escritura
# ----------------------------------------------------------------------


def _verificar_proveedor(db: Session, proveedor_id: int | None) -> None:
    """
    Comprueba que el proveedor asignado exista, reutilizando la capa
    crud del módulo de proveedores (lanza `ProveedorNoEncontrado` -> 404
    con el mismo cuerpo de error común). Se valida ANTES de insertar,
    así el error es un 404 explícito y no el 409 genérico de "SKU
    duplicado" que produciría la clave foránea al reventar.
    """
    if proveedor_id is not None:
        crud_proveedores.obtener_por_id(db, proveedor_id)


def _traducir_integrity_error(db: Session, error: IntegrityError, sku: str | None) -> None:
    """Convierte el error de la base de datos en `SkuDuplicado` (criterio 52)."""
    db.rollback()
    raise SkuDuplicado(sku) from error


def crear(db: Session, datos: dict) -> Producto:
    _verificar_proveedor(db, datos.get("proveedor_id"))
    producto = Producto(**datos)
    db.add(producto)
    try:
        db.commit()
    except IntegrityError as error:
        _traducir_integrity_error(db, error, datos.get("sku"))
    db.refresh(producto)
    return producto


def reemplazar(db: Session, producto: Producto, datos: dict) -> Producto:
    """PUT: reemplazo total de los campos editables por el cliente."""
    _verificar_proveedor(db, datos.get("proveedor_id"))
    for campo, valor in datos.items():
        setattr(producto, campo, valor)
    try:
        db.commit()
    except IntegrityError as error:
        _traducir_integrity_error(db, error, datos.get("sku"))
    db.refresh(producto)
    return producto


def cambiar_estado(db: Session, producto: Producto, activo: bool) -> Producto:
    """Publica o despublica un producto sin borrarlo."""
    producto.activo = activo
    db.commit()
    db.refresh(producto)
    return producto


def eliminar(db: Session, producto: Producto) -> None:
    """
    Elimina un producto. Si ya fue comprado (FK en
    `pedido_items.producto_id`, sin ON DELETE CASCADE a propósito para
    no romper el historial de compras) se lanza `ProductoConPedidos`
    (409) en vez de dejar que la base rechace el DELETE con un 500.
    """
    asociados = contar_pedidos(db, producto.id)
    if asociados > 0:
        raise ProductoConPedidos()

    db.delete(producto)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ProductoConPedidos() from error
